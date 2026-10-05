import httpx
import pytest


@pytest.mark.parametrize('name,args,method,path,extra',[
    ('pause_playback',{},'PUT','pause',{}),('resume_playback',{},'PUT','play',{}),
    ('next_track',{},'POST','next',{}),('previous_track',{},'POST','previous',{}),
    ('seek_playback',{'position_ms':1234},'PUT','seek',{'position_ms':1234}),
    ('set_volume',{'volume_percent':25},'PUT','volume',{'volume_percent':25}),
    ('set_shuffle',{'state':True},'PUT','shuffle',{'state':True}),
    ('set_repeat',{'state':'context'},'PUT','repeat',{'state':'context'})])
def test_direct_controls_target_device(fake_http,fake_device,name,args,method,path,extra):
    from spotify_mcp_assistant import playback
    fake_http.enqueue_devices([fake_device]);fake_http.enqueue(httpx.Response(204))
    data=getattr(playback,name)(device_id='test-mac',**args)
    assert data['status']=='submitted'
    assert len(fake_http.write_calls)==1
    call=fake_http.write_calls[0]
    assert call['method']==method and call['path']=='/me/player/'+path
    assert call['params']=={'device_id':'test-mac',**extra}
    assert not call.get('json')


@pytest.mark.parametrize('name,args',[('set_volume',{'volume_percent':-1}),('set_volume',{'volume_percent':101}),('seek_playback',{'position_ms':-1}),('set_repeat',{'state':'invalid'})])
def test_control_bounds_prevent_http(fake_http,name,args):
    from spotify_mcp_assistant import playback
    from pydantic import ValidationError
    with pytest.raises(ValidationError): getattr(playback,name)(device_id='test-mac',**args)
    assert fake_http.calls==[]


@pytest.mark.parametrize('devices',[[],[{'id':None,'name':'Test','type':'computer','is_restricted':False}], [{'id':'test-mac','name':'Test','type':'computer','is_restricted':True}]])
def test_unusable_device_stops_control(fake_http,devices):
    from spotify_mcp_assistant import playback,spotify_client
    fake_http.enqueue_devices(devices)
    with pytest.raises(spotify_client.SpotifyError):playback.pause_playback('test-mac')
    assert fake_http.write_count==0


def test_play_track_starts_from_beginning(fake_http,fake_device):
    from spotify_mcp_assistant import playback
    fake_http.enqueue_devices([fake_device]);fake_http.enqueue(httpx.Response(204))
    data=playback.play_track('spotify:track:'+'a'*22,'test-mac',dry_run=False)
    assert data['status']=='submitted'
    assert fake_http.write_calls[0]['json']=={'uris':['spotify:track:'+'a'*22]}


def test_playback_missing_controls_are_unknown(fake_http):
    from spotify_mcp_assistant import playback
    fake_http.enqueue(httpx.Response(200,json={'is_playing':True,'device':{'id':'test-mac','name':'Test'}}))
    data=playback.get_playback_state()
    assert data['shuffle_state'] is None
    assert data['device']['volume_percent'] is None


@pytest.mark.parametrize('name,args',[('play_playlist',{'playlist_uri':'spotify:playlist:'+'p'*22}),('transfer_playback',{}),('add_to_queue',{'track_uri':'spotify:track:'+'a'*22})])
def test_context_writes_preview_by_default(fake_http,fake_device,name,args):
    from spotify_mcp_assistant import playback
    fake_http.enqueue_devices([fake_device])
    assert getattr(playback,name)(device_id='test-mac',**args)['status']=='preview'
    assert fake_http.write_count==0


@pytest.mark.parametrize('name,args,method,path,body,params',[
    ('play_playlist',{'playlist_uri':'spotify:playlist:'+'p'*22},'PUT','play',{'context_uri':'spotify:playlist:'+'p'*22},{'device_id':'test-mac'}),
    ('transfer_playback',{},'PUT','',{'device_ids':['test-mac'],'play':False},None),
    ('add_to_queue',{'track_uri':'spotify:track:'+'a'*22},'POST','queue',None,{'device_id':'test-mac','uri':'spotify:track:'+'a'*22})])
def test_context_write_payloads(fake_http,fake_device,name,args,method,path,body,params):
    from spotify_mcp_assistant import playback
    fake_http.enqueue_devices([fake_device]);fake_http.enqueue(httpx.Response(204))
    getattr(playback,name)(device_id='test-mac',dry_run=False,**args)
    call=fake_http.write_calls[0]
    assert call['method']==method
    assert call['path']=='/me/player'+('/'+path if path else '')
    assert call.get('json')==body
    assert call['params']==params


def test_queue_preserves_non_tracks(fake_http,fake_track):
    from spotify_mcp_assistant import playback
    fake_http.enqueue(httpx.Response(200,json={'currently_playing':None,'queue':[fake_track,{'type':'episode'},None]}))
    data=playback.get_queue()
    assert data['currently_playing'] is None
    assert [entry['item_type'] for entry in data['queue']]==['track','episode','unavailable']


def test_playlist_write_timeout_not_replayed(fake_http,fake_device):
    from spotify_mcp_assistant import playback,spotify_client
    fake_http.enqueue_devices([fake_device]);fake_http.enqueue(httpx.ReadTimeout('fake'))
    with pytest.raises(spotify_client.SpotifyError) as caught:
        playback.play_playlist('spotify:playlist:'+'p'*22,'test-mac',dry_run=False)
    assert caught.value.data['status']=='unknown'
    assert fake_http.write_count==1


def test_refresh_failure_before_context_write_is_not_unknown(fake_http,fake_device,monkeypatch):
    from spotify_mcp_assistant import playback,spotify_client
    fake_http.enqueue_devices([fake_device])
    count=0
    def token(**kw):
        nonlocal count
        count+=1
        if count>1:raise httpx.ReadTimeout('fake refresh')
        return 'fake'
    monkeypatch.setattr(spotify_client,'get_access_token',token)
    with pytest.raises(spotify_client.SpotifyError) as caught:
        playback.play_playlist('spotify:playlist:'+'p'*22,'test-mac',dry_run=False)
    assert caught.value.error['code']=='network_error'
    assert caught.value.data['status']!='unknown'
    assert fake_http.write_count==0
