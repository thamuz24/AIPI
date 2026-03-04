import base64
import binascii
import ctypes
import json
import os
import random
import re
import shutil
import threading
import time
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

MODEL_NAME = os.getenv('AIPA_TEXT_MODEL', 'google/flan-t5-base')
OLLAMA_MODEL_NAME = os.getenv('AIPA_OLLAMA_MODEL', 'qwen2.5:7b').strip()
OLLAMA_BASE_URL = os.getenv('AIPA_OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/')
OPENAI_MODEL_NAME = os.getenv('AIPA_OPENAI_MODEL', 'gpt-oss-120b').strip()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '').strip()
OPENAI_BASE_URL = os.getenv('AIPA_OPENAI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
GEMINI_MODEL_NAME = os.getenv('AIPA_GEMINI_MODEL', 'gemma-3-27b-it').strip()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', os.getenv('AIPA_GEMINI_API_KEY', '')).strip()
GEMINI_BASE_URL = os.getenv('AIPA_GEMINI_URL', 'https://generativelanguage.googleapis.com/v1beta').rstrip('/')
HF_FALLBACK_ENABLED = os.getenv('AIPA_ENABLE_HF_FALLBACK', '0').strip().lower() in {'1', 'true', 'yes'}
WEB_SEARCH_ENABLED = os.getenv('AIPA_ENABLE_WEB_SEARCH', '1').strip().lower() in {'1', 'true', 'yes'}
WEB_SEARCH_MODE = os.getenv('AIPA_WEB_SEARCH_MODE', 'smart').strip().lower()
SERPER_API_KEY = os.getenv('SERPER_API_KEY', '').strip()
SERPER_URL = os.getenv('SERPER_URL', 'https://google.serper.dev/search').strip()
SERPAPI_API_KEY = os.getenv('SERPAPI_API_KEY', '').strip()
PORT = int(os.getenv('AIPA_CONTROLL_PORT', '8001'))
HOST = os.getenv('AIPA_CONTROLL_HOST', '0.0.0.0')
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / 'knowledge_store.json'
CONVERSATION_FILE = BASE_DIR / 'conversation_store.json'
KEYWORD_TRAIN_DIR = BASE_DIR / 'model' / 'keyword_train'
WEB_SEARCH_INTENT_FILE = KEYWORD_TRAIN_DIR / 'web_search_intent_keywords.txt'
WEB_SEARCH_FRESHNESS_FILE = KEYWORD_TRAIN_DIR / 'web_search_freshness_keywords.txt'
WEB_SEARCH_FORCED_FILE = KEYWORD_TRAIN_DIR / 'web_search_forced_keywords.txt'
COMPUTER_CONTROL_TRAIN_FILE = KEYWORD_TRAIN_DIR / 'computer_control_train.txt'
COMPUTER_CONTROL_ENABLED = os.getenv('AIPA_ENABLE_COMPUTER_CONTROL', '1').strip().lower() in {'1', 'true', 'yes'}
COMPUTER_CONTROL_ROOT = Path(os.getenv('AIPA_COMPUTER_CONTROL_ROOT', str(BASE_DIR))).resolve()
COMPUTER_CONTROL_ALLOW_ANY_PATH = os.getenv('AIPA_COMPUTER_CONTROL_ALLOW_ANY_PATH', '0').strip().lower() in {
    '1',
    'true',
    'yes',
}
COMPUTER_CONTROL_ALLOW_DELETE = os.getenv('AIPA_COMPUTER_CONTROL_ALLOW_DELETE', '1').strip().lower() in {
    '1',
    'true',
    'yes',
}
CONTROL_READ_PREVIEW_LIMIT = int(os.getenv('AIPA_CONTROL_READ_PREVIEW_LIMIT', '2500'))
CONTROL_LIST_LIMIT = int(os.getenv('AIPA_CONTROL_LIST_LIMIT', '50'))

DEFAULT_WEB_SEARCH_INTENT_KEYWORDS = [
    'tim tren google',
    'tim tren mang',
    'tim kiem',
    'tra cuu',
    'tim nguon',
    'nguon tham khao',
    'cho minh nguon',
    'cho xin nguon',
    'trich dan nguon',
    'dinh kem link',
    'gui link',
    'tai lieu',
    'tai lieu tham khao',
    'tai lieu hoc',
    'tai lieu chinh thuc',
    'tai lieu huong dan',
    'paper',
    'pdf',
    'documentation',
    'tai lieu api',
    'api docs',
    'wiki',
    'wikipedia',
    'fact check',
    'kiem chung',
]

DEFAULT_WEB_SEARCH_FRESHNESS_KEYWORDS = [
    'hom nay',
    'moi nhat',
    'tin tuc',
    'cap nhat',
    'gia',
    'gia vang',
    'gia usd',
    'ty gia',
    'thoi tiet',
    'lich thi dau',
    'ket qua tran',
]

DEFAULT_WEB_SEARCH_FORCED_KEYWORDS = [
    'lam the nao',
    'ban co biet',
    'vi sao',
]

WORD_CHAIN_LEXICON = [
    'học sinh',
    'sinh viên',
    'viên chức',
    'chức năng',
    'năng lượng',
    'lượng giác',
    'giác quan',
    'quan tâm',
    'tâm lý',
    'lý thuyết',
    'thuyết phục',
    'phục vụ',
    'vụ việc',
    'việc làm',
    'làm việc',
    'công nghệ',
    'nghệ thuật',
    'thuật toán',
    'toán học',
    'học tập',
    'tập trung',
    'trung tâm',
    'tâm sự',
    'sự thật',
    'thật thà',
    'thà rằng',
    'rằng buộc',
    'buộc tội',
    'tội phạm',
    'phạm vi',
    'vi mô',
    'mô hình',
    'hình học',
    'hình ảnh',
    'ảnh hưởng',
    'hưởng ứng',
    'ứng dụng',
    'dụng cụ',
    'cụ thể',
    'thể thao',
    'thao tác',
    'tác dụng',
    'dụng ý',
    'ý tưởng',
    'tưởng tượng',
    'tượng hình',
    'văn học',
    'học đường',
    'đường phố',
    'phố cổ',
    'cổ điển',
    'điển hình',
    'hình thức',
    'thức ăn',
    'ăn uống',
    'uống nước',
    'nước hoa',
    'hoa quả',
    'quả bóng',
    'bóng đá',
    'đá bóng',
    'âm nhạc',
    'nhạc cụ',
    'cụm từ',
    'từ điển',
    'điện thoại',
    'thoại kịch',
    'kịch bản',
    'bản đồ',
    'đồ dùng',
    'dùng thử',
    'thử thách',
    'thách thức',
    'môi trường',
    'trường học',
    'tình bạn',
    'bạn bè',
    'bè bạn',
    'hòa bình',
    'bình luận',
    'luận văn',
    'văn hóa',
    'hóa học',
    'học viện',
    'viện trợ',
    'trợ giúp',
    'giúp việc',
    'game thủ',
    'thủ công',
    'luật chơi',
    'chơi game',
]


class ChatMessage(BaseModel):
    sender: Literal['user', 'bot']
    text: str = Field(min_length=1, max_length=3000)


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=3000)
    history: List[ChatMessage] = Field(default_factory=list)
    session_id: Optional[str] = Field(default='default', max_length=120)


class ChatResponse(BaseModel):
    answer: str
    source: Literal['knowledge', 'model', 'fallback', 'web']
    model: str


class TrainRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    answer: str = Field(min_length=1, max_length=3000)


class FaceExtractRequest(BaseModel):
    image: str = Field(min_length=50, max_length=15_000_000)


class FaceExtractResponse(BaseModel):
    status: Literal['ok']
    embedding: List[float]
    dimension: int


class KnowledgeStore:
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.lock = threading.Lock()
        self._pairs = self._load_pairs()

    def _load_pairs(self):
        if not self.file_path.exists():
            return []
        try:
            data = json.loads(self.file_path.read_text(encoding='utf-8'))
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict)]
        except Exception:
            pass
        return []

    def _save_pairs(self):
        self.file_path.write_text(
            json.dumps(self._pairs, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

    @staticmethod
    def _normalize(text: str) -> str:
        return (text or '').strip().lower()

    def add_pair(self, question: str, answer: str):
        q = self._normalize(question)
        a = answer.strip()
        if not q or not a:
            return

        with self.lock:
            existing = next((item for item in self._pairs if self._normalize(item.get('question', '')) == q), None)
            if existing:
                existing['answer'] = a
            else:
                self._pairs.append({'question': question.strip(), 'answer': a})
            self._save_pairs()

    def find_answer(self, question: str) -> Optional[str]:
        if not self._pairs:
            return None

        ask = self._normalize(question)
        best_score = 0.0
        best_answer = None

        for item in self._pairs:
            saved_q = self._normalize(item.get('question', ''))
            if not saved_q:
                continue
            score = SequenceMatcher(None, ask, saved_q).ratio()
            if ask in saved_q or saved_q in ask:
                score = max(score, 0.9)
            if score > best_score:
                best_score = score
                best_answer = item.get('answer')

        if best_score >= 0.78:
            return best_answer
        return None


class ConversationStore:
    def __init__(self, file_path: Path, max_messages: int = 320, max_facts: int = 32):
        self.file_path = file_path
        self.max_messages = max(40, max_messages)
        self.max_facts = max(8, max_facts)
        self.lock = threading.Lock()
        self._sessions = self._load_sessions()

    def _load_sessions(self):
        if not self.file_path.exists():
            return {}

        try:
            raw_data = json.loads(self.file_path.read_text(encoding='utf-8'))
        except Exception:
            return {}

        if not isinstance(raw_data, dict):
            return {}

        sessions = raw_data.get('sessions')
        if not isinstance(sessions, dict):
            return {}

        sanitized = {}
        for key, value in sessions.items():
            if not isinstance(value, dict):
                continue
            sid = self.normalize_session_id(str(key))
            messages = value.get('messages', [])
            facts = value.get('facts', [])
            raw_word_chain = value.get('word_chain', {})
            sanitized[sid] = {
                'messages': [item for item in messages if isinstance(item, dict)],
                'facts': [str(item).strip() for item in facts if str(item).strip()],
                'word_chain': self._sanitize_word_chain_state(raw_word_chain),
                'updated_at': str(value.get('updated_at', '')),
            }
        return sanitized

    def _save_sessions(self):
        payload = {'sessions': self._sessions}
        self.file_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

    @staticmethod
    def normalize_session_id(session_id: Optional[str]) -> str:
        raw = (session_id or 'default').strip().lower()
        safe = re.sub(r'[^a-z0-9._-]', '-', raw)
        safe = re.sub(r'-{2,}', '-', safe).strip('-.')
        return (safe or 'default')[:120]

    @staticmethod
    def _normalize_text(text: str) -> str:
        base = (text or '').lower().strip()
        only_text = ''.join(ch if ch.isalnum() or ch.isspace() else ' ' for ch in base)
        return ' '.join(only_text.split())

    @staticmethod
    def _sanitize_word_chain_state(raw_state: Optional[dict]) -> dict:
        state = raw_state if isinstance(raw_state, dict) else {}
        used = state.get('used', [])
        if not isinstance(used, list):
            used = []
        normalized_used = []
        seen = set()
        for item in used:
            token = str(item).strip().lower()
            if not token or token in seen:
                continue
            seen.add(token)
            normalized_used.append(token)
        return {
            'active': bool(state.get('active', False)),
            'expected': str(state.get('expected', '')).strip().lower(),
            'expected_display': str(state.get('expected_display', '')).strip().lower(),
            'last_bot_phrase': str(state.get('last_bot_phrase', '')).strip(),
            'used': normalized_used[-200:],
        }

    def _ensure_session(self, session_id: str):
        session = self._sessions.get(session_id)
        if not isinstance(session, dict):
            session = {}

        messages = session.get('messages')
        if not isinstance(messages, list):
            messages = []

        facts = session.get('facts')
        if not isinstance(facts, list):
            facts = []

        word_chain = self._sanitize_word_chain_state(session.get('word_chain', {}))

        fixed = {
            'messages': [item for item in messages if isinstance(item, dict)],
            'facts': [str(item).strip() for item in facts if str(item).strip()],
            'word_chain': word_chain,
            'updated_at': str(session.get('updated_at', '')),
        }
        self._sessions[session_id] = fixed
        return fixed

    @classmethod
    def _extract_facts(cls, user_text: str) -> List[str]:
        clean = cls._normalize_text(user_text)
        if not clean or clean.endswith('?'):
            return []

        facts = []
        direct_patterns = [
            ('toi ten la ', 'Ten nguoi dung la {}.'),
            ('minh ten la ', 'Ten nguoi dung la {}.'),
            ('ten toi la ', 'Ten nguoi dung la {}.'),
            ('my name is ', 'Ten nguoi dung la {}.'),
            ('toi la ', 'Nguoi dung la {}.'),
            ('minh la ', 'Nguoi dung la {}.'),
            ('i am ', 'Nguoi dung la {}.'),
            ('toi thich ', 'So thich cua nguoi dung: {}.'),
            ('minh thich ', 'So thich cua nguoi dung: {}.'),
            ('i like ', 'So thich cua nguoi dung: {}.'),
            ('muc tieu cua toi la ', 'Muc tieu cua nguoi dung: {}.'),
            ('toi dang lam ', 'Nguoi dung dang lam: {}.'),
            ('minh dang lam ', 'Nguoi dung dang lam: {}.'),
        ]

        for prefix, template in direct_patterns:
            if clean.startswith(prefix):
                value = cls._shorten_fact_value(clean[len(prefix):])
                if 2 <= len(value) <= 80:
                    facts.append(template.format(value))

        if len(clean) <= 80 and clean.startswith('toi o ') and len(clean) > len('toi o '):
            location = cls._shorten_fact_value(clean[len('toi o '):])
            if location:
                facts.append(f'Nguoi dung o {location}.')

        # Return a small number of high-signal facts to avoid noisy memory.
        return facts[:3]

    @classmethod
    def _shorten_fact_value(cls, value: str) -> str:
        cleaned = cls._normalize_text(value)
        split_markers = [
            ' va toi ',
            ' va minh ',
            ' va em ',
            ' nhung ',
            ' because ',
            ' and i ',
            ' and my ',
        ]
        for marker in split_markers:
            if marker in cleaned:
                cleaned = cleaned.split(marker, 1)[0]
        return cleaned.strip(' .,;:')

    def get_recent_messages(self, session_id: Optional[str], limit: int = 30) -> List[ChatMessage]:
        sid = self.normalize_session_id(session_id)
        with self.lock:
            session = self._ensure_session(sid)
            raw_messages = list(session.get('messages', []))

        output: List[ChatMessage] = []
        for item in raw_messages[-max(1, limit):]:
            sender = item.get('sender')
            text = str(item.get('text', '')).strip()
            if sender not in {'user', 'bot'} or not text:
                continue
            try:
                output.append(ChatMessage(sender=sender, text=text))
            except Exception:
                continue
        return output

    def get_facts(self, session_id: Optional[str], limit: int = 12) -> List[str]:
        sid = self.normalize_session_id(session_id)
        with self.lock:
            session = self._ensure_session(sid)
            facts = [str(item).strip() for item in session.get('facts', []) if str(item).strip()]
        return facts[-max(1, limit):]

    def append_exchange(self, session_id: Optional[str], user_text: str, bot_text: str):
        sid = self.normalize_session_id(session_id)
        user_clean = (user_text or '').strip()
        bot_clean = (bot_text or '').strip()
        if not user_clean and not bot_clean:
            return

        with self.lock:
            session = self._ensure_session(sid)
            now = datetime.utcnow().isoformat(timespec='seconds') + 'Z'

            if user_clean:
                session['messages'].append({'sender': 'user', 'text': user_clean, 'at': now})
            if bot_clean:
                session['messages'].append({'sender': 'bot', 'text': bot_clean, 'at': now})

            if len(session['messages']) > self.max_messages:
                session['messages'] = session['messages'][-self.max_messages:]

            existing_facts = session.get('facts', [])
            seen = {self._normalize_text(item) for item in existing_facts}
            for fact in self._extract_facts(user_clean):
                key = self._normalize_text(fact)
                if key and key not in seen:
                    existing_facts.append(fact)
                    seen.add(key)

            if len(existing_facts) > self.max_facts:
                existing_facts = existing_facts[-self.max_facts:]

            session['facts'] = existing_facts
            session['updated_at'] = now
            self._save_sessions()

    def get_word_chain_state(self, session_id: Optional[str]) -> dict:
        sid = self.normalize_session_id(session_id)
        with self.lock:
            session = self._ensure_session(sid)
            state = self._sanitize_word_chain_state(session.get('word_chain', {}))
        return {
            'active': state['active'],
            'expected': state['expected'],
            'expected_display': state['expected_display'],
            'last_bot_phrase': state['last_bot_phrase'],
            'used': list(state['used']),
        }

    def set_word_chain_state(self, session_id: Optional[str], state: dict):
        sid = self.normalize_session_id(session_id)
        with self.lock:
            session = self._ensure_session(sid)
            session['word_chain'] = self._sanitize_word_chain_state(state)
            session['updated_at'] = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
            self._save_sessions()

    def session_count(self) -> int:
        with self.lock:
            return len(self._sessions)


class WebSearchService:
    def __init__(self, enabled: bool, serper_api_key: str, serper_url: str, serpapi_api_key: str):
        self.enabled = enabled
        self.serper_api_key = serper_api_key
        self.serper_url = serper_url
        self.serpapi_api_key = serpapi_api_key
        self.last_error = ''
        self._cache: Dict[str, Tuple[float, List[dict]]] = {}
        self._cache_ttl_seconds = 1800
        self._cache_max_items = 128
        self._cache_lock = threading.Lock()

    @property
    def active(self) -> bool:
        return self.enabled

    @property
    def google_ready(self) -> bool:
        return bool(self.serper_api_key or self.serpapi_api_key)

    def _search_with_serper(self, prompt: str, limit: int = 3) -> List[dict]:
        self.last_error = ''
        if not self.serper_api_key:
            self.last_error = 'Chưa cấu hình SERPER_API_KEY.'
            return []

        payload = json.dumps(
            {
                'q': prompt,
                'num': max(1, min(limit, 5)),
                'hl': 'vi',
                'gl': 'vn',
            }
        ).encode('utf-8')

        req = urlrequest.Request(
            url=self.serper_url,
            data=payload,
            headers={
                'X-API-KEY': self.serper_api_key,
                'Content-Type': 'application/json',
            },
            method='POST',
        )

        try:
            with urlrequest.urlopen(req, timeout=8) as response:
                data = json.loads(response.read().decode('utf-8'))
        except urlerror.HTTPError as exc:
            try:
                message = exc.read().decode('utf-8', errors='ignore').strip()
            except Exception:
                message = ''
            detail = message if message else 'Không có chi tiết.'
            self.last_error = f'Serper lỗi HTTP {exc.code}: {detail}'
            return []
        except Exception as exc:
            self.last_error = f'Lỗi kết nối Serper: {exc}'
            return []

        organic = data.get('organic', []) if isinstance(data, dict) else []
        results = []
        for item in organic[:limit]:
            if not isinstance(item, dict):
                continue
            title = str(item.get('title', '')).strip()
            snippet = str(item.get('snippet', '')).strip()
            link = str(item.get('link', '')).strip()
            if title and (snippet or link):
                results.append({'title': title, 'snippet': snippet, 'url': link})
        if not results:
            self.last_error = 'Serper không trả về kết quả phù hợp.'
        return results

    def _search_with_serpapi(self, prompt: str, limit: int = 3) -> List[dict]:
        self.last_error = ''
        if not self.serpapi_api_key:
            self.last_error = 'Chưa cấu hình SERPAPI_API_KEY.'
            return []

        params = {
            'engine': 'google',
            'q': prompt,
            'hl': 'vi',
            'gl': 'vn',
            'num': str(max(1, min(limit, 5))),
            'api_key': self.serpapi_api_key,
        }
        url = f"https://serpapi.com/search.json?{urlparse.urlencode(params)}"
        req = urlrequest.Request(url=url, method='GET')

        try:
            with urlrequest.urlopen(req, timeout=8) as response:
                data = json.loads(response.read().decode('utf-8'))
        except urlerror.HTTPError as exc:
            try:
                message = exc.read().decode('utf-8', errors='ignore').strip()
            except Exception:
                message = ''
            detail = message if message else 'Không có chi tiết.'
            self.last_error = f'SerpApi lỗi HTTP {exc.code}: {detail}'
            return []
        except Exception as exc:
            self.last_error = f'Lỗi kết nối SerpApi: {exc}'
            return []

        organic = data.get('organic_results', []) if isinstance(data, dict) else []
        results = []
        for item in organic[:limit]:
            if not isinstance(item, dict):
                continue
            title = str(item.get('title', '')).strip()
            snippet = str(item.get('snippet', '')).strip()
            link = str(item.get('link', '')).strip()
            if title and (snippet or link):
                results.append({'title': title, 'snippet': snippet, 'url': link})

        if not results:
            self.last_error = 'SerpApi không trả về kết quả phù hợp.'
        return results

    def _cache_get(self, prompt: str) -> List[dict]:
        key = _normalize_match(prompt)
        if not key:
            return []
        with self._cache_lock:
            cached = self._cache.get(key)
            if not cached:
                return []
            ts, results = cached
            if (time.time() - ts) > self._cache_ttl_seconds:
                self._cache.pop(key, None)
                return []
            return list(results)

    def _cache_set(self, prompt: str, results: List[dict]):
        key = _normalize_match(prompt)
        if not key or not results:
            return
        with self._cache_lock:
            if len(self._cache) >= self._cache_max_items:
                oldest_key = min(self._cache.items(), key=lambda item: item[1][0])[0]
                self._cache.pop(oldest_key, None)
            self._cache[key] = (time.time(), list(results))

    @staticmethod
    def _search_with_wikipedia(prompt: str, limit: int = 3) -> List[dict]:
        encoded = urlparse.quote(prompt)
        url = (
            'https://vi.wikipedia.org/w/api.php?action=opensearch'
            f'&search={encoded}&limit={max(1, min(limit, 5))}&namespace=0&format=json'
        )
        req = urlrequest.Request(url=url, method='GET')
        try:
            with urlrequest.urlopen(req, timeout=8) as response:
                data = json.loads(response.read().decode('utf-8'))
        except Exception:
            return []

        if not isinstance(data, list) or len(data) < 4:
            return []

        titles = data[1] if isinstance(data[1], list) else []
        snippets = data[2] if isinstance(data[2], list) else []
        urls = data[3] if isinstance(data[3], list) else []
        results = []
        for idx, title in enumerate(titles[:limit]):
            t = str(title).strip()
            s = str(snippets[idx]).strip() if idx < len(snippets) else ''
            u = str(urls[idx]).strip() if idx < len(urls) else ''
            if t and (s or u):
                results.append({'title': t, 'snippet': s, 'url': u})
        return results

    def search_google(self, prompt: str, limit: int = 3) -> List[dict]:
        if not self.active:
            return []
        cached = self._cache_get(prompt)
        if cached:
            self.last_error = ''
            return cached[:limit]

        # Prioritize SerpApi because many users provide SerpApi key for Google search.
        results = self._search_with_serpapi(prompt, limit=limit) if self.serpapi_api_key else []
        if not results and self.serper_api_key:
            results = self._search_with_serper(prompt, limit=limit)

        if results:
            self._cache_set(prompt, results)
        return results

    def search(self, prompt: str, limit: int = 3) -> List[dict]:
        return self.search_google(prompt, limit=limit)


def _should_use_web_search(prompt: str) -> bool:
    if _should_force_google_lookup(prompt):
        return True

    clean = _normalize_match_ascii(prompt)
    if not clean:
        return False

    search_intent_keywords = _load_keyword_list_from_txt(
        WEB_SEARCH_INTENT_FILE,
        DEFAULT_WEB_SEARCH_INTENT_KEYWORDS,
    )
    freshness_keywords = _load_keyword_list_from_txt(
        WEB_SEARCH_FRESHNESS_FILE,
        DEFAULT_WEB_SEARCH_FRESHNESS_KEYWORDS,
    )
    return any(keyword in clean for keyword in search_intent_keywords + freshness_keywords)


def _should_force_google_lookup(prompt: str) -> bool:
    clean = _normalize_match_ascii(prompt)
    if not clean:
        return False

    forced_keywords = _load_keyword_list_from_txt(
        WEB_SEARCH_FORCED_FILE,
        DEFAULT_WEB_SEARCH_FORCED_KEYWORDS,
    )
    return any(keyword in clean for keyword in forced_keywords)


def _build_web_answer(results: List[dict]) -> str:
    lines = ['Mình đã tra cứu nhanh từ nguồn web, tóm tắt như sau:']
    for idx, item in enumerate(results[:3], start=1):
        title = str(item.get('title', '')).strip()
        snippet = str(item.get('snippet', '')).strip()
        url = str(item.get('url', '')).strip()
        if snippet:
            lines.append(f'{idx}. {title}: {snippet}')
        else:
            lines.append(f'{idx}. {title}')
        if url:
            lines.append(f'Nguồn: {url}')
    return '\n'.join(lines)


def _build_web_context(results: List[dict]) -> str:
    context_lines = []
    for idx, item in enumerate(results[:3], start=1):
        title = str(item.get('title', '')).strip()
        snippet = str(item.get('snippet', '')).strip()
        url = str(item.get('url', '')).strip()
        if title or snippet:
            context_lines.append(f'{idx}. {title} - {snippet}'.strip(' -'))
        if url:
            context_lines.append(f'Nguồn {idx}: {url}')
    return '\n'.join(context_lines)


def _compose_prompt_with_web_context(prompt: str, web_results: List[dict]) -> str:
    web_context = _build_web_context(web_results)
    if not web_context:
        return prompt
    return (
        'Bạn là trợ lý tiếng Việt. Hãy ưu tiên thông tin từ kết quả Google sau, '
        'trả lời ngắn gọn, rõ ràng, và không bịa thêm.\n\n'
        f'Kết quả Google:\n{web_context}\n\n'
        f'Câu hỏi người dùng: {prompt}'
    )


def _merge_histories(memory_history: List[ChatMessage], request_history: List[ChatMessage]) -> List[ChatMessage]:
    merged: List[ChatMessage] = []
    seen = set()
    for item in list(memory_history)[-32:] + list(request_history)[-16:]:
        text = (item.text or '').strip()
        if not text:
            continue
        key = f'{item.sender}|{text}'
        if key in seen:
            continue
        seen.add(key)
        merged.append(ChatMessage(sender=item.sender, text=text))
    return merged[-40:]


class TextModel:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._generator = None
        self._lock = threading.Lock()

    def _get_generator(self):
        if self._generator is not None:
            return self._generator

        with self._lock:
            if self._generator is not None:
                return self._generator

            from transformers import pipeline

            self._generator = pipeline('text2text-generation', model=self.model_name)
            return self._generator

    def generate(self, prompt: str, history: List[ChatMessage], memory_facts: Optional[List[str]] = None) -> str:
        generator = self._get_generator()
        recent = history[-6:]
        history_lines = '\n'.join(
            f"{'Nguoi dung' if item.sender == 'user' else 'Tro ly'}: {item.text}" for item in recent
        )
        facts = [item.strip() for item in (memory_facts or []) if item and item.strip()]
        memory_block = ''
        if facts:
            memory_block = (
                'Thong tin da biet ve nguoi dung (uu tien tan dung, khong hoi lai khi da du thong tin):\n'
                + '\n'.join(f'- {item}' for item in facts[-10:])
                + '\n\n'
            )

        composed_prompt = (
            'Bạn là trợ lý AI tiếng Việt cho hệ thống AIPA. '
            'Luôn trả lời bằng tiếng Việt có dấu, đúng trọng tâm, rõ ràng, thân thiện, không lan man. '
            'Trả lời ngắn gọn, tối đa 4 câu và không dùng markdown rườm rà. '
            'Chỉ dùng ngôn ngữ khác khi người dùng yêu cầu rõ ràng.\n\n'
            f'{memory_block}'
            f"Hội thoại gần đây:\n{history_lines if history_lines else '(không có)'}\n\n"
            f'Người dùng: {prompt}\n'
            'Trợ lý:'
        )

        output = generator(
            composed_prompt,
            max_new_tokens=120,
            do_sample=False,
            repetition_penalty=1.08,
        )

        if not output:
            return ''

        return str(output[0].get('generated_text', '')).strip()


class CloudChatModel:
    def __init__(self, model_name: str, api_key: str, base_url: str):
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self._client = None
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.model_name and self.base_url)

    def _get_client(self):
        if not self.api_key:
            return None

        if self._client is not None:
            return self._client

        with self._lock:
            if self._client is not None:
                return self._client

            from openai import OpenAI

            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            return self._client

    def generate(self, prompt: str, history: List[ChatMessage], memory_facts: Optional[List[str]] = None) -> str:
        if not self.enabled:
            return ''

        client = self._get_client()
        if client is None:
            return ''

        messages = [
            {
                'role': 'system',
                'content': (
                    'Bạn là trợ lý AI tiếng Việt cho hệ thống AIPA. '
                    'Luôn trả lời bằng tiếng Việt có dấu, rõ ràng, logic, ưu tiên chính xác, '
                    'ngắn gọn nếu câu hỏi đơn giản. Trả lời tối đa 4 câu, không markdown rườm rà. '
                    'Chỉ dùng ngôn ngữ khác khi người dùng yêu cầu.'
                ),
            }
        ]
        facts = [item.strip() for item in (memory_facts or []) if item and item.strip()]
        if facts:
            messages.append(
                {
                    'role': 'system',
                    'content': (
                        'Thong tin da biet ve nguoi dung, hay tai su dung de tranh hoi lap lai:\n'
                        + '\n'.join(f'- {item}' for item in facts[-10:])
                    ),
                }
            )

        for item in history[-8:]:
            role = 'user' if item.sender == 'user' else 'assistant'
            messages.append({'role': role, 'content': item.text})

        messages.append({'role': 'user', 'content': prompt})

        response = client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.35,
            max_tokens=160,
        )

        if not response.choices:
            return ''

        content = response.choices[0].message.content
        return (content or '').strip()


class GeminiChatModel:
    def __init__(self, model_name: str, api_key: str, base_url: str):
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.last_error = ''

    @property
    def enabled(self) -> bool:
        return bool(self.model_name and self.api_key)

    def generate(self, prompt: str, history: List[ChatMessage], memory_facts: Optional[List[str]] = None) -> str:
        self.last_error = ''
        if not self.enabled:
            self.last_error = 'Chưa cấu hình GEMINI_API_KEY.'
            return ''

        facts = [item.strip() for item in (memory_facts or []) if item and item.strip()]
        history_lines = '\n'.join(
            f"{'Người dùng' if item.sender == 'user' else 'Trợ lý'}: {item.text}"
            for item in history[-10:]
        )
        facts_block = '\n'.join(f'- {item}' for item in facts[-10:]) if facts else '(không có)'

        composed_prompt = (
            'Bạn là trợ lý AI tiếng Việt cho hệ thống AIPA. '
            'Luôn trả lời bằng tiếng Việt có dấu, chính xác, rõ ràng, đúng trọng tâm, tối đa 4 câu. '
            'Không dùng markdown rườm rà.\n\n'
            f'Thông tin đã biết về người dùng:\n{facts_block}\n\n'
            f'Hội thoại gần đây:\n{history_lines if history_lines else "(không có)"}\n\n'
            f'Người dùng: {prompt}\n'
            'Trợ lý:'
        )

        payload = {
            'contents': [
                {
                    'role': 'user',
                    'parts': [{'text': composed_prompt}],
                }
            ],
            'generationConfig': {
                'temperature': 0.35,
                'maxOutputTokens': 320,
            },
        }

        def parse_error_message(raw_text: str) -> str:
            try:
                parsed = json.loads(raw_text)
                if isinstance(parsed, dict):
                    err = parsed.get('error')
                    if isinstance(err, dict):
                        msg = str(err.get('message', '')).strip()
                        if msg:
                            return msg
            except Exception:
                pass
            return (raw_text or '').strip()

        model_candidates = []
        for model_name in [self.model_name, 'gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-latest']:
            cleaned = str(model_name).strip()
            if cleaned and cleaned not in model_candidates:
                model_candidates.append(cleaned)

        for model_name in model_candidates:
            key = urlparse.quote(self.api_key, safe='')
            url = f'{self.base_url}/models/{model_name}:generateContent?key={key}'
            req = urlrequest.Request(
                url=url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST',
            )

            try:
                with urlrequest.urlopen(req, timeout=60) as response:
                    raw = response.read().decode('utf-8')
                    data = json.loads(raw)
            except urlerror.HTTPError as exc:
                try:
                    error_body = exc.read().decode('utf-8')
                except Exception:
                    error_body = str(exc)
                message = parse_error_message(error_body) or str(exc)
                self.last_error = f'Gemini {model_name} lỗi HTTP {exc.code}: {message}'
                if exc.code == 404:
                    continue
                return ''
            except (urlerror.URLError, TimeoutError, ValueError) as exc:
                self.last_error = f'Lỗi kết nối Gemini: {exc}'
                return ''

            if not isinstance(data, dict):
                self.last_error = f'Gemini {model_name} trả về dữ liệu không hợp lệ.'
                continue

            if isinstance(data.get('error'), dict):
                message = str(data['error'].get('message', '')).strip() or 'Gemini trả lỗi không xác định.'
                self.last_error = f'Gemini {model_name}: {message}'
                continue

            candidates = data.get('candidates', [])
            if not isinstance(candidates, list) or not candidates:
                self.last_error = f'Gemini {model_name} không trả về nội dung.'
                continue

            first = candidates[0] if isinstance(candidates[0], dict) else {}
            content = first.get('content') if isinstance(first, dict) else {}
            parts = content.get('parts') if isinstance(content, dict) else []
            if not isinstance(parts, list):
                self.last_error = f'Gemini {model_name} trả về định dạng không hợp lệ.'
                continue

            text_chunks = []
            for part in parts:
                if not isinstance(part, dict):
                    continue
                text = str(part.get('text', '')).strip()
                if text:
                    text_chunks.append(text)

            text_output = '\n'.join(text_chunks).strip()
            if text_output:
                return text_output
            self.last_error = f'Gemini {model_name} không có text khả dụng.'

        return ''


class OllamaChatModel:
    def __init__(self, model_name: str, base_url: str):
        self.model_name = model_name
        self.base_url = base_url

    @property
    def enabled(self) -> bool:
        return bool(self.model_name and self.base_url)

    def generate(self, prompt: str, history: List[ChatMessage], memory_facts: Optional[List[str]] = None) -> str:
        if not self.enabled:
            return ''

        messages = [
            {
                'role': 'system',
                'content': (
                    'Bạn là trợ lý AI tiếng Việt cho hệ thống AIPA. '
                    'Luôn trả lời bằng tiếng Việt có dấu, chính xác, ngắn gọn, đúng trọng tâm câu hỏi. '
                    'Trả lời tối đa 4 câu, không markdown rườm rà. '
                    'Chỉ dùng ngôn ngữ khác khi người dùng yêu cầu.'
                ),
            }
        ]
        facts = [item.strip() for item in (memory_facts or []) if item and item.strip()]
        if facts:
            messages.append(
                {
                    'role': 'system',
                    'content': (
                        'Thong tin da biet ve nguoi dung, hay tai su dung de tranh hoi lap lai:\n'
                        + '\n'.join(f'- {item}' for item in facts[-10:])
                    ),
                }
            )

        for item in history[-8:]:
            messages.append(
                {
                    'role': 'user' if item.sender == 'user' else 'assistant',
                    'content': item.text,
                }
            )
        messages.append({'role': 'user', 'content': prompt})

        payload = {
            'model': self.model_name,
            'messages': messages,
            'stream': False,
            'options': {
                'temperature': 0.3,
                'num_ctx': 4096,
                'num_predict': 160,
            },
        }

        req = urlrequest.Request(
            url=f'{self.base_url}/api/chat',
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )

        try:
            with urlrequest.urlopen(req, timeout=60) as response:
                raw = response.read().decode('utf-8')
                data = json.loads(raw)
        except (urlerror.URLError, urlerror.HTTPError, TimeoutError, ValueError):
            return ''

        message = data.get('message') if isinstance(data, dict) else None
        if not isinstance(message, dict):
            return ''

        return str(message.get('content', '')).strip()


class FaceEmbeddingService:
    def __init__(self):
        self._encoder = None
        self._lock = threading.Lock()

    def _get_encoder(self):
        if self._encoder is not None:
            return self._encoder

        with self._lock:
            if self._encoder is not None:
                return self._encoder

            try:
                from face.face_encoder import FaceEncoder
            except ImportError:
                from face_encoder import FaceEncoder

            self._encoder = FaceEncoder()
            return self._encoder

    @staticmethod
    def _decode_image(image_data: str):
        payload = (image_data or '').strip()
        if payload.startswith('data:'):
            _, _, payload = payload.partition(',')

        if not payload:
            raise ValueError('Du lieu anh rong.')

        try:
            raw_bytes = base64.b64decode(payload, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError('Du lieu anh khong hop le (base64).') from exc

        frame_bytes = np.frombuffer(raw_bytes, dtype=np.uint8)
        frame = cv2.imdecode(frame_bytes, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError('Khong giai ma duoc anh.')
        return frame

    def extract_embedding(self, image_data: str) -> Optional[List[float]]:
        frame = self._decode_image(image_data)
        encoder = self._get_encoder()
        embedding = encoder.get_embedding(frame)
        if embedding is None:
            return None
        return np.asarray(embedding, dtype=float).flatten().tolist()



def _normalize_match(text: str) -> str:
    base = (text or '').lower().strip()
    only_text = ''.join(ch if ch.isalnum() or ch.isspace() else ' ' for ch in base)
    return ' '.join(only_text.split())


def _remove_vietnamese_tone(text: str) -> str:
    lowered = (text or '').lower()
    lowered = lowered.replace('đ', 'd')
    normalized = unicodedata.normalize('NFD', lowered)
    return ''.join(ch for ch in normalized if unicodedata.category(ch) != 'Mn')


def _normalize_match_ascii(text: str) -> str:
    return _remove_vietnamese_tone(_normalize_match(text))


_KEYWORD_FILE_CACHE: Dict[str, Tuple[Optional[int], List[str]]] = {}
_KEYWORD_FILE_CACHE_LOCK = threading.Lock()
_CONTROL_RULE_CACHE: Tuple[Optional[int], List[dict]] = (None, [])


def _load_keyword_list_from_txt(file_path: Path, fallback_keywords: List[str]) -> List[str]:
    cache_key = str(file_path)
    file_mtime: Optional[int] = None
    if file_path.exists():
        try:
            file_mtime = file_path.stat().st_mtime_ns
        except OSError:
            file_mtime = None

    with _KEYWORD_FILE_CACHE_LOCK:
        cached = _KEYWORD_FILE_CACHE.get(cache_key)
        if cached and cached[0] == file_mtime:
            return cached[1]

    raw_lines: List[str] = []
    if file_path.exists():
        try:
            raw_lines = file_path.read_text(encoding='utf-8').splitlines()
        except Exception:
            raw_lines = []

    if not raw_lines:
        raw_lines = fallback_keywords

    normalized_keywords: List[str] = []
    for raw_line in raw_lines:
        candidate = str(raw_line).strip()
        if not candidate or candidate.startswith('#'):
            continue
        normalized = _normalize_match_ascii(candidate)
        if normalized and normalized not in normalized_keywords:
            normalized_keywords.append(normalized)

    if not normalized_keywords:
        normalized_keywords = [_normalize_match_ascii(item) for item in fallback_keywords if _normalize_match_ascii(item)]

    with _KEYWORD_FILE_CACHE_LOCK:
        _KEYWORD_FILE_CACHE[cache_key] = (file_mtime, normalized_keywords)
    return normalized_keywords


def _load_computer_control_rules() -> List[dict]:
    global _CONTROL_RULE_CACHE

    file_mtime: Optional[int] = None
    if COMPUTER_CONTROL_TRAIN_FILE.exists():
        try:
            file_mtime = COMPUTER_CONTROL_TRAIN_FILE.stat().st_mtime_ns
        except OSError:
            file_mtime = None

    cached_mtime, cached_rules = _CONTROL_RULE_CACHE
    if cached_mtime == file_mtime:
        return cached_rules

    rules: List[dict] = []
    if COMPUTER_CONTROL_TRAIN_FILE.exists():
        try:
            lines = COMPUTER_CONTROL_TRAIN_FILE.read_text(encoding='utf-8').splitlines()
        except Exception:
            lines = []
    else:
        lines = []

    for raw_line in lines:
        line = str(raw_line).strip()
        if not line or line.startswith('#'):
            continue
        if '=>' not in line:
            continue
        trigger_part, action_part = line.split('=>', 1)
        trigger_display = trigger_part.strip()
        trigger_key = _normalize_match_ascii(trigger_display)
        if not trigger_key:
            continue
        actions = [item.strip() for item in action_part.split('||') if item.strip()]
        if not actions:
            continue
        rules.append(
            {
                'trigger': trigger_key,
                'trigger_display': trigger_display,
                'actions': actions,
            }
        )

    rules.sort(key=lambda item: len(str(item.get('trigger', ''))), reverse=True)
    _CONTROL_RULE_CACHE = (file_mtime, rules)
    return rules


def _extract_prompt_tail(prompt: str, trigger_key: str) -> str:
    raw_prompt = (prompt or '').strip()
    clean_prompt = _normalize_match_ascii(raw_prompt)
    if not trigger_key or not clean_prompt.startswith(trigger_key):
        return ''

    prompt_words = raw_prompt.split()
    trigger_word_count = len(trigger_key.split())
    if len(prompt_words) >= trigger_word_count:
        head_words = ' '.join(prompt_words[:trigger_word_count])
        if _normalize_match_ascii(head_words) == trigger_key:
            return ' '.join(prompt_words[trigger_word_count:]).strip()

    return clean_prompt[len(trigger_key):].strip()


def _strip_control_prompt_prefix(prompt: str) -> str:
    raw = (prompt or '').strip()
    pattern = r'^\s*(giọng nói|giong noi|voice)\s*[:\-]?\s*'
    return re.sub(pattern, '', raw, flags=re.IGNORECASE).strip()


def _render_control_value(value: str, prompt: str, prompt_tail: str) -> str:
    rendered = str(value or '')
    rendered = rendered.replace('{PROMPT}', prompt or '')
    rendered = rendered.replace('{PROMPT_CLEAN}', _normalize_match_ascii(prompt))
    rendered = rendered.replace('{REST}', prompt_tail or '')
    rendered = rendered.replace('{NOW}', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    rendered = rendered.replace('{NL}', '\n')
    return rendered.strip()


def _resolve_control_path(raw_path: str) -> Path:
    raw = (raw_path or '').strip()
    if not raw:
        raise ValueError('Thieu duong dan trong tap lenh.')

    expanded = os.path.expandvars(os.path.expanduser(raw))
    path_obj = Path(expanded)
    if not path_obj.is_absolute():
        path_obj = COMPUTER_CONTROL_ROOT / path_obj
    resolved = path_obj.resolve()

    if not COMPUTER_CONTROL_ALLOW_ANY_PATH:
        try:
            resolved.relative_to(COMPUTER_CONTROL_ROOT)
        except ValueError as exc:
            raise PermissionError(
                f'Duong dan ngoai vung cho phep: {resolved.as_posix()} (root: {COMPUTER_CONTROL_ROOT.as_posix()})'
            ) from exc
    return resolved


def _read_file_preview(path: Path) -> str:
    data = path.read_bytes()
    if b'\x00' in data[:1024]:
        return f'File nhi phan: {path.as_posix()} ({len(data)} bytes).'

    text = data.decode('utf-8-sig', errors='replace')
    if len(text) > CONTROL_READ_PREVIEW_LIMIT:
        text = text[:CONTROL_READ_PREVIEW_LIMIT].rstrip() + '...'
    return f'Noi dung {path.as_posix()}:\n{text}'


def _list_dir_preview(path: Path) -> str:
    items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    preview_items = items[: max(1, CONTROL_LIST_LIMIT)]
    lines = []
    for item in preview_items:
        kind = 'DIR' if item.is_dir() else 'FILE'
        lines.append(f'- [{kind}] {item.name}')
    if len(items) > len(preview_items):
        lines.append(f'... ({len(items) - len(preview_items)} muc khac)')
    body = '\n'.join(lines) if lines else '(trong)'
    return f'Danh sach {path.as_posix()}:\n{body}'


def _ensure_deletion_allowed(path: Path):
    if not COMPUTER_CONTROL_ALLOW_DELETE:
        raise PermissionError('Xoa file/thu muc dang bi tat. Bat AIPA_COMPUTER_CONTROL_ALLOW_DELETE=1 de su dung.')

    if path == COMPUTER_CONTROL_ROOT:
        raise PermissionError('Khong duoc xoa thu muc root cua computer control.')
    if path.parent == path:
        raise PermissionError('Khong duoc xoa thu muc goc he thong.')


def _extract_time_token(text: str) -> str:
    candidate = str(text or '').strip()
    if not candidate:
        return ''

    pattern = re.compile(r'(?<!\d)(\d{1,2}[:.]\d{2}(?:\s*[APap]\.?[Mm]\.?)?)')
    match = pattern.search(candidate)
    if not match:
        return ''
    token = re.sub(r'\s+', ' ', match.group(1)).strip()
    return token.replace('.', ':')


def _scan_desktop_clock_text() -> str:
    if os.name != 'nt':
        return 'Khong ho tro quet dong ho desktop tren he dieu hanh nay.'

    try:
        user32 = ctypes.windll.user32
    except Exception as exc:
        return f'Khong truy cap duoc WinAPI de quet desktop clock: {exc}'

    get_class_name = user32.GetClassNameW
    get_class_name.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
    get_class_name.restype = ctypes.c_int

    get_window_text = user32.GetWindowTextW
    get_window_text.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
    get_window_text.restype = ctypes.c_int

    find_window = user32.FindWindowW
    find_window.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
    find_window.restype = ctypes.c_void_p

    enum_child_windows = user32.EnumChildWindows
    enum_child_windows.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    enum_child_windows.restype = ctypes.c_int

    taskbar_hwnd = find_window('Shell_TrayWnd', None)
    if not taskbar_hwnd:
        return 'Khong tim thay taskbar de quet dong ho desktop.'

    entries: List[Tuple[str, str]] = []

    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def _callback(hwnd, _lparam):
        class_buf = ctypes.create_unicode_buffer(256)
        text_buf = ctypes.create_unicode_buffer(512)
        get_class_name(hwnd, class_buf, len(class_buf))
        get_window_text(hwnd, text_buf, len(text_buf))
        class_name = str(class_buf.value or '').strip()
        text = str(text_buf.value or '').strip()
        if class_name or text:
            entries.append((class_name, text))
        return True

    callback_ref = enum_proc(_callback)
    enum_child_windows(taskbar_hwnd, callback_ref, 0)

    prioritized = []
    for class_name, text in entries:
        class_key = class_name.lower()
        score = 0
        if class_name == 'TrayClockWClass':
            score += 10
        if 'clock' in class_key:
            score += 5
        if _extract_time_token(text):
            score += 3
        if text:
            score += 1
        prioritized.append((score, class_name, text))

    prioritized.sort(key=lambda item: item[0], reverse=True)
    for _, class_name, text in prioritized:
        token = _extract_time_token(text)
        if token:
            return f'Da quet desktop clock: {token} (class={class_name or "unknown"})'

    now_local = datetime.now().strftime('%H:%M:%S')
    return f'Khong doc duoc text dong ho tu desktop. Gio he thong hien tai: {now_local}.'


def _execute_computer_control_action(action_text: str, prompt: str, prompt_tail: str) -> str:
    raw_action = str(action_text or '').strip()
    if not raw_action:
        raise ValueError('Action trong.')

    parts = [part.strip() for part in raw_action.split('|')]
    command = parts[0].upper()

    if command in {'SCAN_DESKTOP_CLOCK', 'CHECK_DESKTOP_CLOCK', 'SCANDESKTOPCLOCK', 'CHECKDESKTOPCLOCK'}:
        return _scan_desktop_clock_text()

    if command in {'OPEN_FILE', 'READ_FILE', 'OPEN', 'READ'}:
        if len(parts) < 2:
            raise ValueError(f'Action {command} can 1 tham so duong dan.')
        file_path = _resolve_control_path(_render_control_value(parts[1], prompt, prompt_tail))
        if not file_path.exists():
            raise FileNotFoundError(f'Khong tim thay: {file_path.as_posix()}')
        if file_path.is_dir():
            return _list_dir_preview(file_path)
        return _read_file_preview(file_path)

    if command in {'LIST_DIR', 'LS'}:
        if len(parts) < 2:
            raise ValueError(f'Action {command} can 1 tham so duong dan.')
        dir_path = _resolve_control_path(_render_control_value(parts[1], prompt, prompt_tail))
        if not dir_path.exists():
            raise FileNotFoundError(f'Khong tim thay: {dir_path.as_posix()}')
        if not dir_path.is_dir():
            raise NotADirectoryError(f'Khong phai thu muc: {dir_path.as_posix()}')
        return _list_dir_preview(dir_path)

    if command in {'WRITE_FILE', 'WRITE'}:
        if len(parts) < 3:
            raise ValueError(f'Action {command} can duong dan va noi dung.')
        file_path = _resolve_control_path(_render_control_value(parts[1], prompt, prompt_tail))
        content_raw = '|'.join(parts[2:])
        content = _render_control_value(content_raw, prompt, prompt_tail)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
        return f'Da ghi de file: {file_path.as_posix()} ({len(content)} ky tu).'

    if command in {'APPEND_FILE', 'APPEND'}:
        if len(parts) < 3:
            raise ValueError(f'Action {command} can duong dan va noi dung.')
        file_path = _resolve_control_path(_render_control_value(parts[1], prompt, prompt_tail))
        content_raw = '|'.join(parts[2:])
        content = _render_control_value(content_raw, prompt, prompt_tail)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open('a', encoding='utf-8') as handler:
            handler.write(content)
        return f'Da them vao file: {file_path.as_posix()} ({len(content)} ky tu).'

    if command in {'CREATE_FILE', 'TOUCH_FILE'}:
        if len(parts) < 2:
            raise ValueError(f'Action {command} can 1 tham so duong dan.')
        file_path = _resolve_control_path(_render_control_value(parts[1], prompt, prompt_tail))
        content_raw = '|'.join(parts[2:]) if len(parts) > 2 else ''
        content = _render_control_value(content_raw, prompt, prompt_tail)
        if file_path.exists():
            return f'File da ton tai: {file_path.as_posix()}'
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
        return f'Da tao file: {file_path.as_posix()}'

    if command in {'CREATE_DIR', 'MKDIR', 'CREATE_FOLDER'}:
        if len(parts) < 2:
            raise ValueError(f'Action {command} can 1 tham so duong dan.')
        dir_path = _resolve_control_path(_render_control_value(parts[1], prompt, prompt_tail))
        dir_path.mkdir(parents=True, exist_ok=True)
        return f'Da tao thu muc: {dir_path.as_posix()}'

    if command in {'DELETE_FILE', 'REMOVE_FILE'}:
        if len(parts) < 2:
            raise ValueError(f'Action {command} can 1 tham so duong dan.')
        file_path = _resolve_control_path(_render_control_value(parts[1], prompt, prompt_tail))
        _ensure_deletion_allowed(file_path)
        if not file_path.exists():
            return f'Khong tim thay de xoa: {file_path.as_posix()}'
        if file_path.is_dir():
            raise IsADirectoryError(f'Duong dan la thu muc, dung DELETE_DIR: {file_path.as_posix()}')
        file_path.unlink()
        return f'Da xoa file: {file_path.as_posix()}'

    if command in {'DELETE_DIR', 'RMDIR', 'REMOVE_DIR'}:
        if len(parts) < 2:
            raise ValueError(f'Action {command} can 1 tham so duong dan.')
        dir_path = _resolve_control_path(_render_control_value(parts[1], prompt, prompt_tail))
        _ensure_deletion_allowed(dir_path)
        if not dir_path.exists():
            return f'Khong tim thay de xoa: {dir_path.as_posix()}'
        if not dir_path.is_dir():
            raise NotADirectoryError(f'Khong phai thu muc: {dir_path.as_posix()}')
        shutil.rmtree(dir_path)
        return f'Da xoa thu muc: {dir_path.as_posix()}'

    if command in {'DELETE_PATH', 'DELETE', 'REMOVE'}:
        if len(parts) < 2:
            raise ValueError(f'Action {command} can 1 tham so duong dan.')
        path = _resolve_control_path(_render_control_value(parts[1], prompt, prompt_tail))
        _ensure_deletion_allowed(path)
        if not path.exists():
            return f'Khong tim thay de xoa: {path.as_posix()}'
        if path.is_dir():
            shutil.rmtree(path)
            return f'Da xoa thu muc: {path.as_posix()}'
        path.unlink()
        return f'Da xoa file: {path.as_posix()}'

    raise ValueError(f'Action khong ho tro: {command}')


def _try_execute_computer_control(prompt: str) -> Optional[str]:
    if not COMPUTER_CONTROL_ENABLED:
        return None

    rules = _load_computer_control_rules()
    if not rules:
        return None

    prompt_for_control = _strip_control_prompt_prefix(prompt)
    clean_prompt = _normalize_match_ascii(prompt_for_control)
    if not clean_prompt:
        return None

    matched_rule = None
    for rule in rules:
        trigger = str(rule.get('trigger', '')).strip()
        if not trigger:
            continue
        if clean_prompt == trigger or clean_prompt.startswith(f'{trigger} '):
            matched_rule = rule
            break

    if not matched_rule:
        return None

    trigger_display = str(matched_rule.get('trigger_display', '')).strip() or str(matched_rule.get('trigger', ''))
    prompt_tail = _extract_prompt_tail(prompt_for_control, str(matched_rule.get('trigger', '')))
    action_logs = []
    for idx, action in enumerate(matched_rule.get('actions', []), start=1):
        try:
            result = _execute_computer_control_action(str(action), prompt_for_control, prompt_tail)
            action_logs.append(f'{idx}. {result}')
        except Exception as exc:
            action_logs.append(f'{idx}. Loi: {exc}')
            break

    if not action_logs:
        return None
    return f'Da thuc thi tap lenh train: "{trigger_display}"\n' + '\n'.join(action_logs)


def _normalize_word_chain_phrase(text: str) -> str:
    clean = _normalize_match(text)
    return ' '.join(clean.split()[:4])


def _word_chain_phrase_key(text: str) -> str:
    return _normalize_match_ascii(text)


def _word_chain_first_key(text: str) -> str:
    parts = _word_chain_phrase_key(text).split()
    return parts[0] if parts else ''


def _word_chain_last_key(text: str) -> str:
    parts = _word_chain_phrase_key(text).split()
    return parts[-1] if parts else ''


def _word_chain_last_display(text: str) -> str:
    parts = _normalize_word_chain_phrase(text).split()
    return parts[-1] if parts else ''


def _word_chain_candidates_for_start(start_key: str, used_keys: set) -> List[str]:
    candidates = [
        phrase for phrase in WORD_CHAIN_LEXICON
        if _word_chain_first_key(phrase) == start_key and _word_chain_phrase_key(phrase) not in used_keys
    ]
    if not candidates:
        return []

    def continuation_score(phrase: str) -> int:
        next_start = _word_chain_last_key(phrase)
        return sum(
            1
            for item in WORD_CHAIN_LEXICON
            if _word_chain_first_key(item) == next_start and _word_chain_phrase_key(item) not in used_keys
        )

    return sorted(candidates, key=lambda item: (continuation_score(item), len(item)), reverse=True)


def _build_word_chain_fallback_phrase(required_display: str, used_keys: set) -> Optional[str]:
    endings = ['học', 'viên', 'thuật', 'lý', 'văn', 'sử', 'đạo', 'đức', 'hóa', 'pháp', 'trình']
    prefix = _normalize_word_chain_phrase(required_display)
    if not prefix:
        return None

    for ending in endings:
        if _normalize_match_ascii(ending) == _normalize_match_ascii(prefix):
            continue
        candidate = f'{prefix} {ending}'
        key = _word_chain_phrase_key(candidate)
        if key and key not in used_keys:
            return candidate
    return None


def _choose_word_chain_seed() -> str:
    starters = ['học sinh', 'công nghệ', 'âm nhạc', 'hòa bình', 'môi trường']
    return random.choice(starters)


def _is_word_chain_start(clean_ascii: str) -> bool:
    return any(
        marker in clean_ascii
        for marker in (
            'noi tu',
            'choi noi tu',
            'bat dau noi tu',
            'choi tro noi tu',
        )
    )


def _is_word_chain_stop(clean_ascii: str) -> bool:
    return any(
        marker in clean_ascii
        for marker in (
            'dung noi tu',
            'thoat noi tu',
            'ket thuc noi tu',
            'nghi choi noi tu',
            'stop noi tu',
        )
    )


def _is_word_chain_guide(clean_ascii: str) -> bool:
    return any(
        marker in clean_ascii
        for marker in (
            'luat noi tu',
            'huong dan noi tu',
            'cach choi noi tu',
        )
    )


def _word_chain_help_message() -> str:
    return (
        'Luật nối từ: từ của bạn phải bắt đầu bằng tiếng cuối của từ trước đó, '
        'không lặp lại từ đã dùng. '
        'Gõ "chơi nối từ" để bắt đầu và "dừng nối từ" để thoát.'
    )


def _handle_word_chain_prompt(prompt: str, session_id: Optional[str], store: ConversationStore) -> Optional[str]:
    clean_ascii = _normalize_match_ascii(prompt)
    state = store.get_word_chain_state(session_id)

    if _is_word_chain_stop(clean_ascii):
        if state.get('active'):
            store.set_word_chain_state(
                session_id,
                {
                    'active': False,
                    'expected': '',
                    'expected_display': '',
                    'last_bot_phrase': '',
                    'used': [],
                },
            )
            return 'Đã dừng trò chơi nối từ. Khi muốn chơi lại, bạn chỉ cần gõ "chơi nối từ".'
        return 'Hiện tại chưa có ván nối từ nào đang chạy.'

    if _is_word_chain_guide(clean_ascii):
        return _word_chain_help_message()

    if _is_word_chain_start(clean_ascii):
        seed_phrase = _choose_word_chain_seed()
        next_key = _word_chain_last_key(seed_phrase)
        next_display = _word_chain_last_display(seed_phrase)
        store.set_word_chain_state(
            session_id,
            {
                'active': True,
                'expected': next_key,
                'expected_display': next_display,
                'last_bot_phrase': seed_phrase,
                'used': [_word_chain_phrase_key(seed_phrase)],
            },
        )
        return (
            f'Bắt đầu nhé. Mình ra trước: "{seed_phrase}". '
            f'Lượt bạn, hãy nối bằng từ bắt đầu với "{next_display}".'
        )

    if not state.get('active'):
        return None

    user_phrase = _normalize_word_chain_phrase(prompt)
    user_parts = user_phrase.split()
    if not user_parts:
        return 'Bạn gửi một từ hoặc cụm ngắn để nối từ nhé.'

    if len(user_parts) > 4:
        return 'Từ nối nên ngắn gọn (1-4 tiếng) để mình kiểm tra chính xác hơn.'

    expected_key = str(state.get('expected', '')).strip()
    expected_display = str(state.get('expected_display', '')).strip() or expected_key
    first_key = _word_chain_first_key(user_phrase)

    if expected_key and first_key != expected_key:
        return f'Chưa hợp lệ. Từ của bạn phải bắt đầu bằng "{expected_display}".'

    used_keys = set(str(item).strip().lower() for item in state.get('used', []))
    user_key = _word_chain_phrase_key(user_phrase)
    if user_key in used_keys:
        return 'Từ này đã dùng rồi, bạn thử từ khác nhé.'

    used_keys.add(user_key)
    required_start = _word_chain_last_key(user_phrase)
    required_display = _word_chain_last_display(user_phrase) or required_start
    candidates = _word_chain_candidates_for_start(required_start, used_keys)
    if not candidates:
        fallback_phrase = _build_word_chain_fallback_phrase(required_display, used_keys)
        if not fallback_phrase:
            store.set_word_chain_state(
                session_id,
                {
                    'active': False,
                    'expected': '',
                    'expected_display': '',
                    'last_bot_phrase': '',
                    'used': list(used_keys),
                },
            )
            return f'"{user_phrase}" hợp lệ. Mình bí từ rồi, bạn thắng ván này.'
        candidates = [fallback_phrase]

    bot_phrase = candidates[0]
    bot_key = _word_chain_phrase_key(bot_phrase)
    used_keys.add(bot_key)

    next_key = _word_chain_last_key(bot_phrase)
    next_display = _word_chain_last_display(bot_phrase)
    store.set_word_chain_state(
        session_id,
        {
            'active': True,
            'expected': next_key,
            'expected_display': next_display,
            'last_bot_phrase': bot_phrase,
            'used': list(used_keys),
        },
    )

    return (
        f'Hợp lệ. Mình nối: "{bot_phrase}". '
        f'Lượt bạn, bắt đầu bằng "{next_display}".'
    )



def _rule_based_answer(prompt: str) -> Optional[str]:
    clean = _normalize_match(prompt)
    if not clean:
        return None

    now = datetime.now()

    if 'hom nay' in clean and ('ngay bao nhieu' in clean or 'ngay may' in clean):
        return f"Hôm nay là ngày {now.strftime('%d/%m/%Y')}."

    if 'bay gio may gio' in clean or 'may gio' in clean or 'gio hien tai' in clean:
        return f"Bây giờ là {now.strftime('%H:%M')} ngày {now.strftime('%d/%m/%Y')}."

    if clean in {'xin chao', 'chao', 'hello', 'hi'}:
        return 'Chào bạn. Mình đang sẵn sàng hỗ trợ bạn.'

    is_china_marker = any(marker in clean for marker in ('trung quoc', 'trung hoa', 'china'))
    if 'noi chien trung quoc' in clean or 'noi chien trung hoa' in clean or (
        is_china_marker and ('quoc dan dang' in clean or 'dang cong san' in clean or 'noi chien' in clean)
    ):
        if 'ai lanh dao' in clean or 'lanh dao' in clean:
            return (
                'Trong Nội chiến Trung Quốc, phe Cộng sản do Mao Trạch Đông lãnh đạo. '
                'Phe Quốc dân đảng do Tưởng Giới Thạch lãnh đạo.'
            )
        return (
            'Nội chiến Trung Quốc (1927-1949, gián đoạn thời kỳ kháng Nhật) diễn ra giữa '
            'Đảng Cộng sản Trung Quốc và Quốc dân đảng. Kết quả là phe Cộng sản thắng lợi, '
            'thành lập nước Cộng hòa Nhân dân Trung Hoa năm 1949.'
        )

    return None


def _contextual_rule_answer(prompt: str, history: List[ChatMessage]) -> Optional[str]:
    clean_prompt = _normalize_match(prompt)
    if not clean_prompt:
        return None

    recent_user_text = ' '.join(
        _normalize_match(item.text)
        for item in history[-14:]
        if item.sender == 'user'
    )
    is_china_marker = any(marker in recent_user_text for marker in ('trung quoc', 'trung hoa', 'china'))
    is_china_civil_war_context = is_china_marker and (
        'noi chien' in recent_user_text or 'quoc dan dang' in recent_user_text or 'dang cong san' in recent_user_text
    )

    if not is_china_civil_war_context:
        return None

    if 'ai lanh dao' in clean_prompt or clean_prompt in {'lanh dao la ai', 'ai la nguoi lanh dao'}:
        return (
            'Trong Nội chiến Trung Quốc, phe Cộng sản do Mao Trạch Đông lãnh đạo, '
            'còn phe Quốc dân đảng do Tưởng Giới Thạch lãnh đạo.'
        )

    if ('cuoc chien do' in clean_prompt and 'dien ra' in clean_prompt) or 'dien ra nhu the nao' in clean_prompt:
        return (
            'Nội chiến Trung Quốc diễn ra theo nhiều giai đoạn từ 1927 đến 1949 '
            '(có gián đoạn thời kỳ kháng Nhật 1937-1945), giữa Quốc dân đảng và '
            'Đảng Cộng sản Trung Quốc; kết cục là phe Cộng sản thắng và lập nước '
            'Cộng hòa Nhân dân Trung Hoa năm 1949.'
        )

    return None



def _is_low_quality_answer(answer: str) -> bool:
    clean = (answer or '').strip().lower()
    if len(clean) < 5:
        return True
    return clean in {'aipa', 'ai', 'tro ly', 'assistant', 'ok', 'vâng', 'vang'}


def _sanitize_language_text(text: str) -> str:
    if not text:
        return ''

    # Keep only Vietnamese/English letters, digits, spaces and common punctuation.
    allowed_punct = set(".,!?;:'\"()[]-/")
    cleaned_chars = []

    for ch in text:
        if ch in {'\n', '\r', '\t', ' '}:
            cleaned_chars.append(ch)
            continue
        if ch.isdigit() or ch in allowed_punct:
            cleaned_chars.append(ch)
            continue

        category = unicodedata.category(ch)
        if category == 'Mn':
            cleaned_chars.append(ch)
            continue

        if category.startswith('L'):
            name = unicodedata.name(ch, '')
            if 'LATIN' in name:
                cleaned_chars.append(ch)
            continue

    text_out = ''.join(cleaned_chars)
    text_out = re.sub(r'[ \t]{2,}', ' ', text_out)
    text_out = re.sub(r'\n{3,}', '\n\n', text_out)
    return text_out.strip()


def _postprocess_answer(answer: str, max_len: int = 1400) -> str:
    clean = (answer or '').strip()
    if not clean:
        return ''

    clean = clean.replace('**', '').replace('`', '')
    clean = _sanitize_language_text(clean)
    clean = re.sub(r'\n{3,}', '\n\n', clean)
    clean = clean.strip()

    if len(clean) <= max_len:
        return clean

    clipped = clean[:max_len].rstrip()
    last_space = clipped.rfind(' ')
    if last_space > int(max_len * 0.7):
        clipped = clipped[:last_space]
    return clipped.rstrip(' .,;:') + '...'


def _sanitize_historical_answer(prompt: str, history: List[ChatMessage], answer: str) -> str:
    clean_prompt = _normalize_match(prompt)
    clean_answer = _normalize_match(answer)
    history_text = ' '.join(_normalize_match(item.text) for item in history[-8:])
    context = f'{clean_prompt} {history_text}'

    is_china_marker = any(marker in context for marker in ('trung quoc', 'trung hoa', 'china'))
    is_china_civil_war_context = is_china_marker and (
        'noi chien' in context or 'quoc dan dang' in context or 'dang cong san' in context
    )
    has_wrong_leader = 'ho chi minh' in clean_answer

    if is_china_civil_war_context and has_wrong_leader:
        if 'lanh dao' in clean_prompt or 'ai' in clean_prompt:
            return (
                'Trong Nội chiến Trung Quốc, phe Cộng sản do Mao Trạch Đông lãnh đạo, '
                'còn phe Quốc dân đảng do Tưởng Giới Thạch lãnh đạo.'
            )
        return (
            'Nội chiến Trung Quốc diễn ra giữa Đảng Cộng sản Trung Quốc và Quốc dân đảng '
            'trong giai đoạn 1927-1949 (gián đoạn thời kỳ kháng Nhật).'
        )

    return answer


app = FastAPI(title='AIPA Controll AI Service', version='1.1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

knowledge_store = KnowledgeStore(DATA_FILE)
conversation_store = ConversationStore(CONVERSATION_FILE)
web_search_service = WebSearchService(WEB_SEARCH_ENABLED, SERPER_API_KEY, SERPER_URL, SERPAPI_API_KEY)
text_model = TextModel(MODEL_NAME)
ollama_chat_model = OllamaChatModel(OLLAMA_MODEL_NAME, OLLAMA_BASE_URL)
cloud_chat_model = CloudChatModel(OPENAI_MODEL_NAME, OPENAI_API_KEY, OPENAI_BASE_URL)
gemini_chat_model = GeminiChatModel(GEMINI_MODEL_NAME, GEMINI_API_KEY, GEMINI_BASE_URL)
face_embedding_service = FaceEmbeddingService()


@app.get('/health')
def health_check():
    return {
        'status': 'ok',
        'model': MODEL_NAME,
        'ollama_model': OLLAMA_MODEL_NAME,
        'ollama_url': OLLAMA_BASE_URL,
        'ollama_enabled': ollama_chat_model.enabled,
        'hf_fallback_enabled': HF_FALLBACK_ENABLED,
        'gemini_model': GEMINI_MODEL_NAME,
        'gemini_enabled': gemini_chat_model.enabled,
        'gemini_last_error': gemini_chat_model.last_error,
        'cloud_model': OPENAI_MODEL_NAME,
        'cloud_base_url': OPENAI_BASE_URL,
        'cloud_enabled': cloud_chat_model.enabled,
        'web_search_enabled': WEB_SEARCH_ENABLED,
        'web_search_mode': WEB_SEARCH_MODE,
        'web_search_google_ready': web_search_service.google_ready,
        'web_search_provider': (
            'serpapi_google'
            if SERPAPI_API_KEY
            else ('serper_google' if SERPER_API_KEY else 'google_not_configured')
        ),
        'web_search_last_error': web_search_service.last_error,
        'computer_control_enabled': COMPUTER_CONTROL_ENABLED,
        'computer_control_train_file': COMPUTER_CONTROL_TRAIN_FILE.as_posix(),
        'computer_control_root': COMPUTER_CONTROL_ROOT.as_posix(),
        'computer_control_allow_any_path': COMPUTER_CONTROL_ALLOW_ANY_PATH,
        'computer_control_allow_delete': COMPUTER_CONTROL_ALLOW_DELETE,
        'knowledge_size': len(knowledge_store._pairs),
        'memory_sessions': conversation_store.session_count(),
    }


@app.post('/api/train')
def train_qa(request: TrainRequest):
    knowledge_store.add_pair(request.question, request.answer)
    return {
        'message': 'Da cap nhat du lieu train thanh cong.',
        'knowledge_size': len(knowledge_store._pairs),
    }


@app.post('/api/chat', response_model=ChatResponse)
def chat(request: ChatRequest):
    session_id = conversation_store.normalize_session_id(request.session_id)
    stored_history = conversation_store.get_recent_messages(session_id, limit=30)
    merged_history = _merge_histories(stored_history, request.history)
    memory_facts = conversation_store.get_facts(session_id, limit=12)
    web_results: List[dict] = []
    prompt_for_model = request.prompt
    web_notice = ''
    force_google_lookup = _should_force_google_lookup(request.prompt)
    should_lookup_web = WEB_SEARCH_ENABLED and (
        force_google_lookup
        or WEB_SEARCH_MODE == 'always'
        or (WEB_SEARCH_MODE != 'off' and _should_use_web_search(request.prompt))
    )

    computer_control_answer = _try_execute_computer_control(request.prompt)
    if computer_control_answer:
        computer_control_answer = _postprocess_answer(computer_control_answer, max_len=1800)
        conversation_store.append_exchange(session_id, request.prompt, computer_control_answer)
        return ChatResponse(answer=computer_control_answer, source='fallback', model='computer_control_train')

    if force_google_lookup:
        if not web_search_service.active:
            forced_fallback = 'Tính năng tra cứu web đang tắt. Bạn hãy bật AIPA_ENABLE_WEB_SEARCH=1.'
            conversation_store.append_exchange(session_id, request.prompt, forced_fallback)
            return ChatResponse(answer=forced_fallback, source='fallback', model='google_forced')
        if not web_search_service.google_ready:
            forced_fallback = (
                'Thiếu API key tra cứu Google. '
                'Bạn hãy cấu hình SERPAPI_API_KEY hoặc SERPER_API_KEY cho câu hỏi dạng làm thế nào/bạn có biết/vì sao.'
            )
            conversation_store.append_exchange(session_id, request.prompt, forced_fallback)
            return ChatResponse(answer=forced_fallback, source='fallback', model='google_forced')

        forced_results = web_search_service.search_google(request.prompt, limit=3)
        if forced_results:
            forced_answer = _postprocess_answer(_build_web_answer(forced_results), max_len=1800)
            conversation_store.append_exchange(session_id, request.prompt, forced_answer)
            return ChatResponse(answer=forced_answer, source='web', model='google_forced')

        forced_fallback = (
            web_search_service.last_error
            or 'Mình chưa lấy được dữ liệu từ Google cho câu hỏi này nên tạm thời không trả lời để tránh sai thông tin.'
        )
        forced_fallback = _postprocess_answer(forced_fallback, max_len=1800)
        conversation_store.append_exchange(session_id, request.prompt, forced_fallback)
        return ChatResponse(answer=forced_fallback, source='fallback', model='google_forced')

    word_chain_answer = _handle_word_chain_prompt(request.prompt, session_id, conversation_store)
    if word_chain_answer:
        word_chain_answer = _postprocess_answer(word_chain_answer)
        conversation_store.append_exchange(session_id, request.prompt, word_chain_answer)
        return ChatResponse(answer=word_chain_answer, source='fallback', model='word_chain')

    learned_answer = knowledge_store.find_answer(request.prompt)
    if learned_answer:
        learned_answer = _postprocess_answer(learned_answer)
        conversation_store.append_exchange(session_id, request.prompt, learned_answer)
        return ChatResponse(answer=learned_answer, source='knowledge', model='knowledge_store')

    rule_answer = _rule_based_answer(request.prompt)
    if rule_answer:
        rule_answer = _postprocess_answer(rule_answer)
        conversation_store.append_exchange(session_id, request.prompt, rule_answer)
        return ChatResponse(answer=rule_answer, source='fallback', model='rule_based')

    contextual_answer = _contextual_rule_answer(request.prompt, merged_history)
    if contextual_answer:
        contextual_answer = _postprocess_answer(contextual_answer)
        conversation_store.append_exchange(session_id, request.prompt, contextual_answer)
        return ChatResponse(answer=contextual_answer, source='fallback', model='contextual_rule')

    if should_lookup_web:
        if not web_search_service.active:
            web_notice = 'Tính năng tra cứu web đang tắt. Bạn hãy bật AIPA_ENABLE_WEB_SEARCH=1.'
        elif not web_search_service.google_ready:
            web_notice = (
                'Thiếu API key tra cứu Google. '
                'Bạn hãy cấu hình SERPAPI_API_KEY hoặc SERPER_API_KEY cho câu hỏi dạng tìm kiếm/tài liệu.'
            )
        else:
            web_results = web_search_service.search_google(request.prompt, limit=3)
            if web_results:
                prompt_for_model = _compose_prompt_with_web_context(request.prompt, web_results)
            else:
                web_notice = (
                    web_search_service.last_error
                    or 'Mình chưa lấy được dữ liệu từ Google cho câu hỏi tìm kiếm/tài liệu này.'
                )

    generated_answer = ''
    local_error = ''
    cloud_error = ''

    if ollama_chat_model.enabled:
        try:
            generated_answer = ollama_chat_model.generate(prompt_for_model, merged_history, memory_facts)
        except Exception as exc:
            generated_answer = ''
            local_error = str(exc)
        generated_answer = _postprocess_answer(generated_answer)
        generated_answer = _sanitize_historical_answer(request.prompt, merged_history, generated_answer)

        if generated_answer and not _is_low_quality_answer(generated_answer):
            conversation_store.append_exchange(session_id, request.prompt, generated_answer)
            return ChatResponse(answer=generated_answer, source='model', model=OLLAMA_MODEL_NAME)

    if HF_FALLBACK_ENABLED:
        try:
            generated_answer = text_model.generate(prompt_for_model, merged_history, memory_facts).strip()
        except Exception as exc:
            generated_answer = ''
            local_error = str(exc)
        generated_answer = _postprocess_answer(generated_answer)
        generated_answer = _sanitize_historical_answer(request.prompt, merged_history, generated_answer)

        if generated_answer and not _is_low_quality_answer(generated_answer):
            conversation_store.append_exchange(session_id, request.prompt, generated_answer)
            return ChatResponse(answer=generated_answer, source='model', model=MODEL_NAME)

    if cloud_chat_model.enabled:
        try:
            generated_answer = cloud_chat_model.generate(prompt_for_model, merged_history, memory_facts)
        except Exception as exc:
            generated_answer = ''
            cloud_error = str(exc)
        generated_answer = _postprocess_answer(generated_answer)
        generated_answer = _sanitize_historical_answer(request.prompt, merged_history, generated_answer)

        if generated_answer and not _is_low_quality_answer(generated_answer):
            conversation_store.append_exchange(session_id, request.prompt, generated_answer)
            return ChatResponse(answer=generated_answer, source='model', model=OPENAI_MODEL_NAME)

    if gemini_chat_model.enabled:
        try:
            generated_answer = gemini_chat_model.generate(prompt_for_model, merged_history, memory_facts)
        except Exception:
            generated_answer = ''
        generated_answer = _postprocess_answer(generated_answer)
        generated_answer = _sanitize_historical_answer(request.prompt, merged_history, generated_answer)

        if generated_answer and not _is_low_quality_answer(generated_answer):
            conversation_store.append_exchange(session_id, request.prompt, generated_answer)
            return ChatResponse(answer=generated_answer, source='model', model=GEMINI_MODEL_NAME)

    if web_results:
        fallback_answer = _build_web_answer(web_results)
    elif should_lookup_web and web_notice:
        fallback_answer = web_notice
    else:
        if HF_FALLBACK_ENABLED:
            fallback_answer = (
                'Minh da nhan cau hoi nhung model local dang khong san sang de tra loi. '
                'Hay kiem tra AIPA_TEXT_MODEL hoac quyen truy cap thu muc model local.'
            )
        elif ollama_chat_model.enabled:
            fallback_answer = (
                'Minh da nhan cau hoi nhung chua ket noi duoc dich vu model local. '
                'Hay kiem tra AIPA_OLLAMA_URL hoac runtime tuong thich Ollama.'
            )
        else:
            fallback_answer = (
                'Minh da nhan cau hoi nhung chua co model local kha dung de tra loi. '
                'Ban co the bat AIPA_ENABLE_HF_FALLBACK=1 hoac cau hinh AIPA_OLLAMA_MODEL/AIPA_OLLAMA_URL.'
            )
    fallback_answer = _postprocess_answer(fallback_answer, max_len=1600)
    if local_error:
        fallback_answer = f'{fallback_answer}\nChi tiết mô hình cục bộ: {local_error}'
    if cloud_error:
        fallback_answer = f'{fallback_answer}\nChi tiết OpenAI: {cloud_error}'
    if gemini_chat_model.enabled and gemini_chat_model.last_error:
        fallback_answer = f'{fallback_answer}\nChi tiết Gemini: {gemini_chat_model.last_error}'
    fallback_answer = _postprocess_answer(fallback_answer, max_len=1800)
    conversation_store.append_exchange(session_id, request.prompt, fallback_answer)
    return ChatResponse(answer=fallback_answer, source='fallback', model='fallback')


@app.post('/api/face/extract', response_model=FaceExtractResponse)
def extract_face_embedding(request: FaceExtractRequest):
    try:
        embedding = face_embedding_service.extract_embedding(request.image)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail='Khong the khoi tao bo ma hoa khuon mat.',
        ) from exc

    if not embedding:
        raise HTTPException(status_code=422, detail='Khong tim thay khuon mat trong anh.')

    return FaceExtractResponse(
        status='ok',
        embedding=embedding,
        dimension=len(embedding),
    )


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('chat_server:app', host=HOST, port=PORT, reload=False)
