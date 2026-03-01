from youtube_transcript_api import YouTubeTranscriptApi
import urllib.parse as urlparse

"""
Skill: youtube_transcript
Description: Extrai legendas e discursos de vídeos do YouTube gratuitamente, sem API Key do Google, permitindo que a IA "assista" a vídeos.
"""

def get_schema():
    return {
        "type": "function",
        "function": {
            "name": "get_youtube_transcript",
            "description": "Extract the written transcript/subtitles of a YouTube video to 'watch' the video content. Completely free, no auth required.",
            "parameters": {
                "type": "object",
                "properties": {
                    "youtube_url_or_id": {
                        "type": "string",
                        "description": "The exact YouTube video URL or Video ID (e.g., 'dQw4w9WgXcQ' or full https link)."
                    }
                },
                "required": ["youtube_url_or_id"]
            }
        }
    }

async def execute(kwargs):
    video_input = kwargs.get("youtube_url_or_id")
    if not video_input:
        return "Erro: 'youtube_url_or_id' obrigatório."

    # Tenta extrair o video_id se enviaram URL
    video_id = video_input
    if "youtube.com" in video_input or "youtu.be" in video_input:
        try:
            parsed = urlparse.urlparse(video_input)
            if "youtu.be" in video_input:
                video_id = parsed.path.lstrip('/')
            else:
                qs = urlparse.parse_qs(parsed.query)
                video_id = qs.get("v", [""])[0]
        except Exception:
            pass

    if not video_id:
        return "Não foi possível extrair o Video ID da URL fornecida."

    try:
        import asyncio
        
        def _get_transcript():
            # Tenta pt, depois en
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt', 'pt-BR', 'en'])
            except:
                # Fallback genérico se der fail de linguagens e tenta traduzir pro english se for chines
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                
            formatter = " ".join([entry['text'] for entry in transcript_list])
            return formatter
            
        full_text = await asyncio.to_thread(_get_transcript)
        
        # Limita para não estourar Janela de Contexto
        if len(full_text) > 8000:
            return full_text[:8000] + "\n\n[TRUNCATED... Vídeo muito longo]"
        return f"Transcrição do Vídeo:\n{full_text}"
        
    except Exception as e:
        return f"Falha na extração de Transcript do YouTube: {e}"
