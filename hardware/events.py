"""Replay decoded batches in timestamp order, including transitions on other knobs."""
from copy import deepcopy


def ordered_frames(groups):
    ordered=[]
    for group,frame in groups.items():
        field='switches' if group.startswith('knob:') else 'active'
        state=dict(frame[field])
        for name,value in reversed(frame['events']):
            if name!='rotation':state[name]=not bool(value)
        for pos,(name,value) in enumerate(frame['events']):
            if name!='rotation':state[name]=bool(value)
            stamp=frame['event_times'][pos]
            item=dict(frame,**{field:dict(state)},events=[(name,value)],event_times=[stamp],captured_ns=stamp)
            # Stable contact levels, not a later release, are needed by the
            # calibration wizard when an entire gesture arrived in one batch.
            item['levels']=dict(frame['levels'])
            for contact,active in state.items():
                if contact in frame.get('released',{}):
                    released=frame['released'][contact]
                    item['levels'][contact]=1-released if active else released
            ordered.append((stamp,0 if group=='panel:lock' and value else 1,group,item))
    ordered.sort(key=lambda item:(item[0],item[1]))
    result=[]
    for stamp,priority,group,frame in ordered:
        name,value=frame['events'][0]
        if result and name=='rotation':
            oldgroup,oldframe=result[-1]
            oldname,oldvalue=oldframe['events'][0]
            if group==oldgroup and oldname=='rotation' and oldvalue*value>0:
                oldframe['events']=[('rotation',oldvalue+value)]
                oldframe['count']=frame['count']
                continue
        result.append((group,frame))
    return result
