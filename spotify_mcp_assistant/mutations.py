"""Progress for sequential writes. A successful response is not verification."""
from spotify_mcp_assistant import spotify_client as api
from spotify_mcp_assistant.models import MutationData, normalize_uris


def mutation(operation, target, parameters, uris=None, deduplicate=False):
    normalized, indices = normalize_uris(uris or [], deduplicate=deduplicate)
    return MutationData(operation=operation,status='preview',target=target,parameters=parameters,
        requested_count=len(uris) if uris is not None else 1,submitted_count=0,
        next_action='Show this preview and wait for a new user confirmation before executing with the same parameters',
        normalized_uris=normalized,input_indices=indices).model_dump(mode='json')


def submit_once(data, submit):
    try:
        response=submit()
    except api.SpotifyError as error:
        if error.error['code'].endswith('result_unknown'):
            data['status']='unknown'
        data['next_action']=error.error['next_action']
        error.data=data
        raise
    data['status']='submitted'
    data['submitted_count']=data['requested_count']
    data['next_action']='Read the affected state to verify the result; do not assume submission is verified'
    return response


def submit_batches(data, batch_size, submit, before=None):
    uris=data['normalized_uris']
    for start in range(0,len(uris),batch_size):
        end=min(start+batch_size,len(uris))
        try:
            if before is not None:
                before(start)
        except api.SpotifyError as error:
            data['status']='partial' if data['submitted_count'] else 'preview'
            data['not_attempted_ranges']=[[start,len(uris)]]
            data['next_action']=error.error['next_action']
            error.data=data
            raise
        try:
            response=submit(uris[start:end],start)
        except api.SpotifyError as error:
            unknown=error.error['code'].endswith('result_unknown')
            data['status']='unknown' if unknown else ('partial' if start else 'preview')
            data['unknown_range' if unknown else 'failed_range']=[start,end]
            data['not_attempted_ranges']=[[end,len(uris)]] if end<len(uris) else []
            data['next_action']=error.error['next_action']
            error.data=data
            raise
        data['submitted_ranges'].append([start,end])
        data['submitted_count']+=end-start
        if response is not None:
            data['snapshot_id']=response.get('snapshot_id',data['snapshot_id'])
    data['status']='submitted'
    data['next_action']='Read the affected state to verify the result; batches are not an atomic transaction'
    return data
