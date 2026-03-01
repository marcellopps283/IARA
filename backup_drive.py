import os
import glob
import datetime
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("backup_drive")

SCOPES = ['https://www.googleapis.com/auth/drive.file']
BACKUP_FOLDER_NAME = 'IARA_Backup'

def get_drive_service():
    creds = None
    # Verifica se já temos o token gerado antes
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # Se não temos credenciais válidas, precisamos logar
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_secrets = glob.glob('client_secret*.json')
            if not client_secrets:
                logger.error("Arquivo client_secret*.json não encontrado na raiz!")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets[0], SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Salva o token para as próximas execuções (inclusive via cron)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
    return build('drive', 'v3', credentials=creds)

def get_or_create_folder(service, folder_name):
    # Procura a pasta
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    
    if not items:
        # Se não existe, cria
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        logger.info(f"Pasta '{folder_name}' criada no Drive.")
        return folder.get('id')
    else:
        return items[0].get('id')

def rotate_backups(service, folder_id):
    query = f"'{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name, createdTime)', orderBy='createdTime desc').execute()
    items = results.get('files', [])
    
    # Mantém os primeiros 7, deleta o resto
    if len(items) > 7:
        items_to_delete = items[7:]
        for item in items_to_delete:
            logger.info(f"Deletando backup antigo para liberar espaço: {item['name']}")
            service.files().delete(fileId=item['id']).execute()

def upload_backup(service, folder_id):
    db_path = config.DB_PATH
    if not os.path.exists(db_path):
        logger.error(f"Arquivo de banco de dados não encontrado em: {db_path}")
        return False
        
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"kittymemory_{timestamp}.db"
    
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    media = MediaFileUpload(str(db_path), mimetype='application/octet-stream', resumable=True)
    
    logger.info(f"Iniciando upload de {filename}...")
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f"Backup concluído: {filename}")
    logger.info(f"Backup concluído com sucesso: {filename}")
    return True

def main():
    try:
        logger.info("Iniciando rotina de Backup pro Google Drive...")
        service = get_drive_service()
        if not service:
            return
            
        folder_id = get_or_create_folder(service, BACKUP_FOLDER_NAME)
        success = upload_backup(service, folder_id)
        
        if success:
            rotate_backups(service, folder_id)
            
    except Exception as e:
        print(f"Erro: {e}")
        logger.error(f"Erro no backup do drive: {e}")

if __name__ == '__main__':
    main()
