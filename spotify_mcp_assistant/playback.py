"""Explicit-device playback controls. Writes are never automatically replayed."""
from typing import Annotated, Literal
from pydantic import TypeAdapter, Field
from spotify_mcp_assistant import spotify_client as api
from spotify_mcp_assistant.models import TrackURI,DeviceID
from spotify_mcp_assistant.mutations import mutation,submit_once

READ_SCOPES=('user-read-playback-state',)
WRITE_SCOPES=('user-modify-playback-state',)


def list_devices() -> list[dict]:
    devices=api.spotify_request('GET','/me/player/devices',required_scopes=READ_SCOPES).json()['devices']
    return [{'device_id':d.get('id'),'name':d.get('name',''),'type':d.get('type',''),
        'is_active':d.get('is_active',False),'is_restricted':d.get('is_restricted',False)} for d in devices]


def require_device(device_id: str, *, devices: list[dict] | None = None) -> dict:
    device_id=TypeAdapter(DeviceID).validate_python(device_id)
    device=next((d for d in (list_devices() if devices is None else devices) if d['device_id']==device_id),None)
    if device is None:
        raise api.SpotifyError('device_unavailable','Selected device is not available','Call list_devices and select a current device ID')
    if device['is_restricted']:
        raise api.SpotifyError('device_restricted','Selected device does not allow control','Select another unrestricted device')
    return device


def get_playback_state() -> dict:
    response=api.spotify_request('GET','/me/player',required_scopes=READ_SCOPES)
    data={} if response.status_code==204 else response.json()
    item=data.get('item');device=data.get('device')
    return {'has_playback':response.status_code!=204,'is_playing':data.get('is_playing',False),
        'progress_ms':data.get('progress_ms'),
        'track':{'name':item['name'],'artists':[a['name'] for a in item['artists']],'track_uri':item['uri']} if item and item.get('type')=='track' else None,
        'device':{'device_id':device.get('id'),'name':device.get('name',''),'volume_percent':device.get('volume_percent'),
                  'supports_volume':device.get('supports_volume')} if device else None,
        'shuffle_state':data.get('shuffle_state'),'repeat_state':data.get('repeat_state'),
        'context_uri':(data.get('context') or {}).get('uri')}


def _play_track(track_uri,device,dry_run):
    if dry_run:
        return {'status':'preview','track_uri':track_uri,'device_id':device['device_id'],'device_name':device['name'],
                'next_action':'Confirm this song and device before playing'}
    api.spotify_request('PUT','/me/player/play',params={'device_id':device['device_id']},json={'uris':[track_uri]},
                        required_scopes=WRITE_SCOPES,unknown_code='playback_result_unknown')
    return {'status':'submitted','track_uri':track_uri,'device_id':device['device_id'],
            'next_action':'Call get_playback_state to verify playback'}


def play_track(track_uri: str, device_id: str, dry_run: bool = True) -> dict:
    TypeAdapter(TrackURI).validate_python(track_uri)
    return _play_track(track_uri,require_device(device_id),dry_run)


def _control(operation,method,path,device_id,extra=None):
    device=require_device(device_id)
    params={'device_id':device['device_id'],**(extra or {})}
    data=mutation(operation,{'device_id':device['device_id']},params)
    submit_once(data,lambda:api.spotify_request(method,'/me/player/'+path,params=params,required_scopes=WRITE_SCOPES))
    return data


def pause_playback(device_id: str) -> dict:
    return _control('pause_playback','PUT','pause',device_id)


def resume_playback(device_id: str) -> dict:
    return _control('resume_playback','PUT','play',device_id)


def next_track(device_id: str) -> dict:
    return _control('next_track','POST','next',device_id)


def previous_track(device_id: str) -> dict:
    return _control('previous_track','POST','previous',device_id)


def seek_playback(position_ms: int, device_id: str) -> dict:
    TypeAdapter(Annotated[int,Field(ge=0)]).validate_python(position_ms)
    return _control('seek_playback','PUT','seek',device_id,{'position_ms':position_ms})


def set_volume(volume_percent: int, device_id: str) -> dict:
    TypeAdapter(Annotated[int,Field(ge=0,le=100)]).validate_python(volume_percent)
    return _control('set_volume','PUT','volume',device_id,{'volume_percent':volume_percent})


def set_shuffle(state: bool, device_id: str) -> dict:
    return _control('set_shuffle','PUT','shuffle',device_id,{'state':state})


def set_repeat(state: str, device_id: str) -> dict:
    TypeAdapter(Literal['off','context','track']).validate_python(state)
    return _control('set_repeat','PUT','repeat',device_id,{'state':state})
