import pytz


def utc_to_local(utc_dt):
    local_tz = pytz.timezone('America/Bogota')
    local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_tz.normalize(local_dt)