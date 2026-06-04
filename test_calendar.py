import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Le decimos a Google que solo queremos LEER el calendario, no modificar nada
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def main():
    creds = None
    # El archivo token.json guarda tus permisos para no pedir login cada vez
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # Si no hay credenciales válidas, te pide iniciar sesión
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Guarda las credenciales para la próxima vez
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    # Conexión con la API de Google Calendar
    service = build('calendar', 'v3', credentials=creds)

    # Obtenemos la hora actual en formato ISO
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    print('Buscando las próximas 3 juntas de tu calendario...')
    
    # Pide los próximos 3 eventos a partir de ahorita
    events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=3, singleEvents=True,
                                              orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        print('No tienes próximas juntas en tu calendario. ¡Día libre!')
        return

    # Imprime los eventos en la terminal
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        # Limpiar un poco el formato de la hora para leerlo fácil
        print(f"- {event['summary']} ({start})")

if __name__ == '__main__':
    main()