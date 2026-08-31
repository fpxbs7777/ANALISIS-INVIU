import requests

def obtener_tokens(username, password):
    """
    Obtiene el bearer token y refresh token de la API de InvertirOnline
    """
    url = 'https://api.invertironline.com/token'
    payload = {
        'username': username,
        'password': password,
        'grant_type': 'password'
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        data = response.json()
        return data.get('access_token'), data.get('refresh_token')
    return None, None

def refrescar_token(refresh_token):
    """
    Refresca el bearer token usando el refresh token
    """
    url = 'https://api.invertironline.com/token'
    payload = {
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        data = response.json()
        return data.get('access_token'), data.get('refresh_token')
    return None, None
