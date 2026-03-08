# -*- coding: utf-8 -*-
import base64
import binascii
import csv
import ctypes
import json
import os
import random
import re
import shutil
import subprocess
import threading
import time
import unicodedata
import zlib
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
COMMON_QA_SEED_FILE = KEYWORD_TRAIN_DIR / 'common_qa_seed_1000.txt'
COMPUTER_CONTROL_TRAIN_FILE = KEYWORD_TRAIN_DIR / 'computer_control_train.txt'
NON_QA_TRAIN_FILES = {
    'web_search_intent_keywords.txt',
    'web_search_freshness_keywords.txt',
    'web_search_forced_keywords.txt',
    'computer_control_train.txt',
}
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
try:
    KNOWLEDGE_VECTOR_DIM = max(64, int(os.getenv('AIPA_KNOWLEDGE_VECTOR_DIM', '256')))
except ValueError:
    KNOWLEDGE_VECTOR_DIM = 256
try:
    KNOWLEDGE_MATCH_THRESHOLD = float(os.getenv('AIPA_KNOWLEDGE_MATCH_THRESHOLD', '0.68'))
except ValueError:
    KNOWLEDGE_MATCH_THRESHOLD = 0.68

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
    'há»c sinh',
    'sinh viĂªn',
    'viĂªn chá»©c',
    'chá»©c nÄƒng',
    'nÄƒng lÆ°á»£ng',
    'lÆ°á»£ng giĂ¡c',
    'giĂ¡c quan',
    'quan tĂ¢m',
    'tĂ¢m lĂ½',
    'lĂ½ thuyáº¿t',
    'thuyáº¿t phá»¥c',
    'phá»¥c vá»¥',
    'vá»¥ viá»‡c',
    'viá»‡c lĂ m',
    'lĂ m viá»‡c',
    'cĂ´ng nghá»‡',
    'nghá»‡ thuáº­t',
    'thuáº­t toĂ¡n',
    'toĂ¡n há»c',
    'há»c táº­p',
    'táº­p trung',
    'trung tĂ¢m',
    'tĂ¢m sá»±',
    'sá»± tháº­t',
    'tháº­t thĂ ',
    'thĂ  ráº±ng',
    'ráº±ng buá»™c',
    'buá»™c tá»™i',
    'tá»™i pháº¡m',
    'pháº¡m vi',
    'vi mĂ´',
    'mĂ´ hĂ¬nh',
    'hĂ¬nh há»c',
    'hĂ¬nh áº£nh',
    'áº£nh hÆ°á»Ÿng',
    'hÆ°á»Ÿng á»©ng',
    'á»©ng dá»¥ng',
    'dá»¥ng cá»¥',
    'cá»¥ thá»ƒ',
    'thá»ƒ thao',
    'thao tĂ¡c',
    'tĂ¡c dá»¥ng',
    'dá»¥ng Ă½',
    'Ă½ tÆ°á»Ÿng',
    'tÆ°á»Ÿng tÆ°á»£ng',
    'tÆ°á»£ng hĂ¬nh',
    'vÄƒn há»c',
    'há»c Ä‘Æ°á»ng',
    'Ä‘Æ°á»ng phá»‘',
    'phá»‘ cá»•',
    'cá»• Ä‘iá»ƒn',
    'Ä‘iá»ƒn hĂ¬nh',
    'hĂ¬nh thá»©c',
    'thá»©c Äƒn',
    'Äƒn uá»‘ng',
    'uá»‘ng nÆ°á»›c',
    'nÆ°á»›c hoa',
    'hoa quáº£',
    'quáº£ bĂ³ng',
    'bĂ³ng Ä‘Ă¡',
    'Ä‘Ă¡ bĂ³ng',
    'Ă¢m nháº¡c',
    'nháº¡c cá»¥',
    'cá»¥m tá»«',
    'tá»« Ä‘iá»ƒn',
    'Ä‘iá»‡n thoáº¡i',
    'thoáº¡i ká»‹ch',
    'ká»‹ch báº£n',
    'báº£n Ä‘á»“',
    'Ä‘á»“ dĂ¹ng',
    'dĂ¹ng thá»­',
    'thá»­ thĂ¡ch',
    'thĂ¡ch thá»©c',
    'mĂ´i trÆ°á»ng',
    'trÆ°á»ng há»c',
    'tĂ¬nh báº¡n',
    'báº¡n bĂ¨',
    'bĂ¨ báº¡n',
    'hĂ²a bĂ¬nh',
    'bĂ¬nh luáº­n',
    'luáº­n vÄƒn',
    'vÄƒn hĂ³a',
    'hĂ³a há»c',
    'há»c viá»‡n',
    'viá»‡n trá»£',
    'trá»£ giĂºp',
    'giĂºp viá»‡c',
    'game thá»§',
    'thá»§ cĂ´ng',
    'luáº­t chÆ¡i',
    'chÆ¡i game',
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
        self.seed_file = COMMON_QA_SEED_FILE
        self.seed_dir = KEYWORD_TRAIN_DIR
        self.lock = threading.Lock()
        self._pairs = self._load_pairs()
        self._seed_pairs: List[dict] = []
        self._seed_signature = ''
        self._refresh_seed_pairs(force=True)

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

    @staticmethod
    def _parse_qa_line(raw_line: str) -> Optional[Tuple[str, str]]:
        line = str(raw_line).strip()
        if not line or line.startswith('#'):
            return None

        qa_match = re.match(r'^(?:q|question|hoi)\s*:\s*(.+?)\s*(?:a|answer|dap)\s*:\s*(.+)$', line, flags=re.IGNORECASE)
        if qa_match:
            question = str(qa_match.group(1)).strip()
            answer = str(qa_match.group(2)).strip()
            if question and answer:
                return question, answer

        for separator in ('=>', '\t', '|'):
            if separator not in line:
                continue
            question_raw, answer_raw = line.split(separator, 1)
            question = str(question_raw).strip()
            answer = str(answer_raw).strip()
            if question and answer:
                return question, answer
        return None

    def _collect_seed_files(self) -> List[Path]:
        files: List[Path] = []
        if self.seed_file.exists():
            files.append(self.seed_file)

        if self.seed_dir.exists():
            for file_path in sorted(self.seed_dir.glob('*.txt')):
                if file_path.name in NON_QA_TRAIN_FILES:
                    continue
                if file_path == self.seed_file:
                    continue
                files.append(file_path)
        return files

    @staticmethod
    def _build_seed_signature(files: List[Path]) -> str:
        parts = []
        for file_path in files:
            try:
                stat = file_path.stat()
                parts.append(f'{file_path.as_posix()}|{stat.st_mtime_ns}|{stat.st_size}')
            except Exception:
                parts.append(f'{file_path.as_posix()}|missing')
        return '||'.join(parts)

    def _load_seed_pairs(self, files: List[Path]) -> List[dict]:
        pairs = []
        for file_path in files:
            try:
                lines = file_path.read_text(encoding='utf-8').splitlines()
            except Exception:
                continue

            for raw_line in lines:
                parsed = self._parse_qa_line(raw_line)
                if not parsed:
                    continue
                question, answer = parsed
                pairs.append({'question': question, 'answer': answer})
        return pairs

    def _refresh_seed_pairs(self, force: bool = False):
        files = self._collect_seed_files()
        signature = self._build_seed_signature(files)
        if not force and signature == self._seed_signature:
            return
        self._seed_pairs = self._load_seed_pairs(files)
        self._seed_signature = signature

    def _combined_pairs(self):
        self._refresh_seed_pairs()
        combined = []
        seen = set()

        for item in self._pairs:
            q = self._normalize(item.get('question', ''))
            if not q:
                continue
            if q in seen:
                continue
            seen.add(q)
            combined.append(item)

        for item in self._seed_pairs:
            q = self._normalize(item.get('question', ''))
            if not q or q in seen:
                continue
            seen.add(q)
            combined.append(item)

        return combined

    def knowledge_size(self):
        return len(self._combined_pairs())

    def _save_pairs(self):
        self.file_path.write_text(
            json.dumps(self._pairs, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

    @staticmethod
    def _normalize(text: str) -> str:
        return (text or '').strip().lower()

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        normalized = _normalize_match_ascii(text)
        return [token for token in re.findall(r'\w+', normalized, flags=re.UNICODE) if len(token) >= 2]

    @staticmethod
    def _vectorize_tokens(tokens: List[str]) -> np.ndarray:
        vec = np.zeros(KNOWLEDGE_VECTOR_DIM, dtype=float)
        for token in tokens:
            if not token:
                continue
            bucket = zlib.crc32(token.encode('utf-8')) % KNOWLEDGE_VECTOR_DIM
            vec[bucket] += 1.0
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec

    @staticmethod
    def _cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
        if left.size == 0 or right.size == 0:
            return 0.0
        return float(np.dot(left, right))

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
        pairs = self._combined_pairs()
        if not pairs:
            return None

        ask = _normalize_match_ascii(question)
        if not ask:
            return None

        ask_tokens = self._tokenize(ask)
        ask_token_set = set(ask_tokens)
        ask_vector = self._vectorize_tokens(ask_tokens)
        best_score = 0.0
        best_answer = None

        for item in pairs:
            saved_q_raw = str(item.get('question', ''))
            saved_a_raw = str(item.get('answer', ''))
            saved_q = _normalize_match_ascii(saved_q_raw)
            if not saved_q:
                continue
            saved_qa = f'{saved_q} {_normalize_match_ascii(saved_a_raw)}'.strip()
            saved_q_tokens = set(self._tokenize(saved_q))
            saved_qa_tokens = self._tokenize(saved_qa)
            saved_qa_token_set = set(saved_qa_tokens)
            saved_vector = self._vectorize_tokens(saved_qa_tokens)

            seq_score = SequenceMatcher(None, ask, saved_q).ratio()

            keyword_q = 0.0
            keyword_qa = 0.0
            if ask_token_set:
                keyword_q = len(ask_token_set.intersection(saved_q_tokens)) / len(ask_token_set)
                keyword_qa = len(ask_token_set.intersection(saved_qa_token_set)) / len(ask_token_set)

            vector_score = self._cosine_similarity(ask_vector, saved_vector)
            score = (
                seq_score * 0.38
                + keyword_q * 0.24
                + keyword_qa * 0.20
                + vector_score * 0.18
            )

            if ask in saved_q or saved_q in ask:
                score = max(score, 0.94)
            elif ask in saved_qa:
                score = max(score, 0.90)
            elif keyword_qa >= 0.8 and vector_score >= 0.45:
                score = min(1.0, score + 0.06)

            if score > best_score:
                best_score = score
                best_answer = saved_a_raw

        if best_score >= KNOWLEDGE_MATCH_THRESHOLD:
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
            self.last_error = 'ChÆ°a cáº¥u hĂ¬nh SERPER_API_KEY.'
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
            detail = message if message else 'KhĂ´ng cĂ³ chi tiáº¿t.'
            self.last_error = f'Serper lá»—i HTTP {exc.code}: {detail}'
            return []
        except Exception as exc:
            self.last_error = f'Lá»—i káº¿t ná»‘i Serper: {exc}'
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
            self.last_error = 'Serper khĂ´ng tráº£ vá» káº¿t quáº£ phĂ¹ há»£p.'
        return results

    def _search_with_serpapi(self, prompt: str, limit: int = 3) -> List[dict]:
        self.last_error = ''
        if not self.serpapi_api_key:
            self.last_error = 'ChÆ°a cáº¥u hĂ¬nh SERPAPI_API_KEY.'
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
            detail = message if message else 'KhĂ´ng cĂ³ chi tiáº¿t.'
            self.last_error = f'SerpApi lá»—i HTTP {exc.code}: {detail}'
            return []
        except Exception as exc:
            self.last_error = f'Lá»—i káº¿t ná»‘i SerpApi: {exc}'
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
            self.last_error = 'SerpApi khĂ´ng tráº£ vá» káº¿t quáº£ phĂ¹ há»£p.'
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
    factual_markers = [
        'o dau',
        'la ai',
        'la gi',
        'khi nao',
        'nam nao',
        'bao nhieu',
        'thu do',
        'nuoc nao',
        'la nuoc nao',
        'co gi',
    ]
    if any(marker in clean for marker in factual_markers):
        return True
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
        if snippet:
            lines.append(f'{idx}. {title}: {snippet}')
        else:
            lines.append(f'{idx}. {title}')
    return '\n'.join(lines)


def _build_web_context(results: List[dict]) -> str:
    context_lines = []
    for idx, item in enumerate(results[:3], start=1):
        title = str(item.get('title', '')).strip()
        snippet = str(item.get('snippet', '')).strip()
        if title or snippet:
            context_lines.append(f'{idx}. {title} - {snippet}'.strip(' -'))
    return '\n'.join(context_lines)


def _compose_prompt_with_web_context(prompt: str, web_results: List[dict]) -> str:
    web_context = _build_web_context(web_results)
    if not web_context:
        return prompt
    return (
        'Ban la tro ly tieng Viet. Hay uu tien thong tin tu ket qua Google sau, '
        'tra loi ngan gon, ro rang, va khong bia them.\n\n'
        f'Ket qua Google:\n{web_context}\n\n'
        f'Cau hoi nguoi dung: {prompt}'
    )


def _looks_like_english_prompt(text: str) -> bool:
    raw = str(text or '').strip()
    if not raw:
        return False

    has_vietnamese_chars = bool(
        re.search('[\u00e0-\u1ef9\u0111]', raw.lower())
    )
    if has_vietnamese_chars:
        return False

    normalized = _normalize_match_ascii(raw)
    tokens = [token for token in normalized.split() if token]
    if not tokens:
        return False

    english_markers = {
        'what', 'why', 'how', 'when', 'where', 'which', 'who',
        'can', 'could', 'should', 'would', 'do', 'does', 'did',
        'please', 'help', 'explain', 'difference', 'between',
        'install', 'setup', 'error', 'issue', 'problem',
        'python', 'javascript', 'react', 'docker', 'linux',
    }
    hit_count = sum(1 for token in tokens if token in english_markers)
    return hit_count >= 1 and len(tokens) >= 2


def _apply_language_instruction(prompt_for_model: str, original_prompt: str) -> str:
    if _looks_like_english_prompt(original_prompt):
        return (
            'Language instruction: The user wrote in English. '
            'Respond in clear natural English, concise, maximum 4 sentences.\n\n'
            f'User prompt:\n{prompt_for_model}'
        )
    return prompt_for_model


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
            'Ban la tro ly AI tieng Viet cho he thong AIPA. '
            'Luon tra loi bang tieng Viet co dau, dung trong tam, ro rang, than thien, khong lan man. '
            'Tra loi ngan gon, toi da 4 cau va khong dung markdown ruom ra. '
            'Chi dung ngon ngu khac khi nguoi dung yeu cau ro rang.\n\n'
            f'{memory_block}'
            f"Hoi thoai gan day:\n{history_lines if history_lines else '(khong co)'}\n\n"
            f'Nguoi dung: {prompt}\n'
            'Tro ly:'
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
                    'Ban la tro ly AI tieng Viet cho he thong AIPA. '
                    'Luon tra loi bang tieng Viet co dau, ro rang, logic, uu tien chinh xac, '
                    'ngan gon neu cau hoi don gian. Tra loi toi da 4 cau, khong markdown ruom ra. '
                    'Chi dung ngon ngu khac khi nguoi dung yeu cau.'
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
            self.last_error = 'Chua cau hinh GEMINI_API_KEY.'
            return ''

        facts = [item.strip() for item in (memory_facts or []) if item and item.strip()]
        history_lines = '\n'.join(
            f"{'Nguoi dung' if item.sender == 'user' else 'Tro ly'}: {item.text}"
            for item in history[-10:]
        )
        facts_block = '\n'.join(f'- {item}' for item in facts[-10:]) if facts else '(khong co)'

        composed_prompt = (
            'Ban la tro ly AI tieng Viet cho he thong AIPA. '
            'Luon tra loi bang tieng Viet co dau, chinh xac, ro rang, dung trong tam, toi da 4 cau. '
            'Khong dung markdown ruom ra.\n\n'
            f'Thong tin da biet ve nguoi dung:\n{facts_block}\n\n'
            f'Hoi thoai gan day:\n{history_lines if history_lines else "(khong co)"}\n\n'
            f'Nguoi dung: {prompt}\n'
            'Tro ly:'
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
                self.last_error = f'Gemini {model_name} loi HTTP {exc.code}: {message}'
                if exc.code == 404:
                    continue
                return ''
            except (urlerror.URLError, TimeoutError, ValueError) as exc:
                self.last_error = f'Loi ket noi Gemini: {exc}'
                return ''

            if not isinstance(data, dict):
                self.last_error = f'Gemini {model_name} tra ve du lieu khong hop le.'
                continue

            if isinstance(data.get('error'), dict):
                message = str(data['error'].get('message', '')).strip() or 'Gemini tra loi khong xac dinh.'
                self.last_error = f'Gemini {model_name}: {message}'
                continue

            candidates = data.get('candidates', [])
            if not isinstance(candidates, list) or not candidates:
                self.last_error = f'Gemini {model_name} khong tra ve noi dung.'
                continue

            first = candidates[0] if isinstance(candidates[0], dict) else {}
            content = first.get('content') if isinstance(first, dict) else {}
            parts = content.get('parts') if isinstance(content, dict) else []
            if not isinstance(parts, list):
                self.last_error = f'Gemini {model_name} tra ve dinh dang khong hop le.'
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
            self.last_error = f'Gemini {model_name} khong co text kha dung.'

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
                    'Ban la tro ly AI tieng Viet cho he thong AIPA. '
                    'Luon tra loi bang tieng Viet co dau, chinh xac, ngan gon, dung trong tam cau hoi. '
                    'Tra loi toi da 4 cau, khong markdown ruom ra. '
                    'Chi dung ngon ngu khac khi nguoi dung yeu cau.'
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
    lowered = lowered.replace(chr(273), 'd').replace(chr(272), 'd')
    normalized = unicodedata.normalize('NFD', lowered)
    return ''.join(ch for ch in normalized if unicodedata.category(ch) != 'Mn')


def _normalize_match_ascii(text: str) -> str:
    return _remove_vietnamese_tone(_normalize_match(text))


_KEYWORD_FILE_CACHE: Dict[str, Tuple[Optional[int], List[str]]] = {}
_KEYWORD_FILE_CACHE_LOCK = threading.Lock()
_CONTROL_RULE_CACHE: Tuple[Optional[int], List[dict]] = (None, [])
_APP_LAUNCHER_CACHE_LOCK = threading.Lock()
_APP_LAUNCHER_CACHE: Tuple[float, Dict[str, Path]] = (0.0, {})
APP_LAUNCHER_CACHE_TTL_SECONDS = max(10, int(os.getenv('AIPA_APP_LAUNCHER_CACHE_TTL', '300')))


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
    pattern = r'^\s*(giong noi|voice)\s*[:\-]?\s*'
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
        raise ValueError('Thiếu đường dẫn trong tập lệnh.')

    expanded = os.path.expandvars(os.path.expanduser(raw))
    path_obj = Path(expanded)
    if not path_obj.is_absolute():
        path_obj = COMPUTER_CONTROL_ROOT / path_obj
    resolved = path_obj.resolve()

    if not COMPUTER_CONTROL_ALLOW_ANY_PATH:
        try:
            resolved.relative_to(COMPUTER_CONTROL_ROOT)
        except ValueError as exc:
            raise PermissionError('Đường dẫn nằm ngoài vùng cho phép.') from exc
    return resolved


def _read_file_preview(path: Path) -> str:
    data = path.read_bytes()
    if b'\x00' in data[:1024]:
        return f'File nhị phân ({len(data)} byte).'

    text = data.decode('utf-8-sig', errors='replace')
    if len(text) > CONTROL_READ_PREVIEW_LIMIT:
        text = text[:CONTROL_READ_PREVIEW_LIMIT].rstrip() + '...'
    return f'Nội dung tệp:\n{text}'


def _list_dir_preview(path: Path) -> str:
    items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    preview_items = items[: max(1, CONTROL_LIST_LIMIT)]
    lines = []
    for item in preview_items:
        kind = 'DIR' if item.is_dir() else 'FILE'
        lines.append(f'- [{kind}] {item.name}')
    if len(items) > len(preview_items):
        lines.append(f'... ({len(items) - len(preview_items)} mục khác)')
    body = '\n'.join(lines) if lines else '(trống)'
    return f'Danh sách mục:\n{body}'


def _ensure_deletion_allowed(path: Path):
    if not COMPUTER_CONTROL_ALLOW_DELETE:
        raise PermissionError('Xóa file/thư mục đang bị tắt. Bật AIPA_COMPUTER_CONTROL_ALLOW_DELETE=1 để sử dụng.')

    if path == COMPUTER_CONTROL_ROOT:
        raise PermissionError('Không được xóa thư mục root của computer control.')
    if path.parent == path:
        raise PermissionError('Không được xóa thư mục gốc hệ thống.')


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
        return 'KhĂ´ng há»— trá»£ quĂ©t Ä‘á»“ng há»“ desktop trĂªn há»‡ Ä‘iá»u hĂ nh nĂ y.'

    try:
        user32 = ctypes.windll.user32
    except Exception as exc:
        return f'KhĂ´ng truy cáº­p Ä‘Æ°á»£c WinAPI Ä‘á»ƒ quĂ©t desktop clock: {exc}'

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
        return 'KhĂ´ng tĂ¬m tháº¥y taskbar Ä‘á»ƒ quĂ©t Ä‘á»“ng há»“ desktop.'

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
    return f'KhĂ´ng Ä‘á»c Ä‘Æ°á»£c text Ä‘á»“ng há»“ tá»« desktop. Giá» há»‡ thá»‘ng hiá»‡n táº¡i: {now_local}.'


def _score_app_name_match(name: str, query: str, tokens: List[str]) -> int:
    name_key = _normalize_match_ascii(name)
    if not name_key:
        return -1

    score = 0
    has_signal = False
    if query and name_key == query:
        score += 120
        has_signal = True
    if query and name_key.startswith(query):
        score += 45
        has_signal = True
    if query and query in name_key:
        score += 30
        has_signal = True

    matched_token_count = 0
    if tokens:
        matched_token_count = sum(1 for token in tokens if token in name_key)
        if matched_token_count > 0:
            has_signal = True
            score += matched_token_count * 8
        if matched_token_count == len(tokens):
            score += 24 + len(tokens) * 3
        if any(token == name_key for token in tokens):
            score += 20
            has_signal = True

    ratio = 0.0
    if query:
        ratio = SequenceMatcher(None, name_key, query).ratio()
        if ratio >= 0.72:
            has_signal = True
            score += int(ratio * 45)
        elif ratio >= 0.60:
            score += int(ratio * 18)

    if not has_signal:
        return -1

    score += max(0, 8 - abs(len(name_key) - len(query)))
    if ' uninstall ' in f' {name_key} ':
        score -= 25
    if query and ratio < 0.45 and matched_token_count == 0:
        score -= 20
    return score


def _extract_executable_path_from_command(command_text: str) -> Optional[Path]:
    raw = str(command_text or '').strip()
    if not raw:
        return None

    if raw.startswith('"'):
        quote_end = raw.find('"', 1)
        if quote_end > 1:
            candidate = raw[1:quote_end]
        else:
            candidate = raw.strip('"')
    else:
        candidate = raw.split(' ', 1)[0]

    if not candidate:
        return None

    expanded = os.path.expandvars(os.path.expanduser(candidate))
    path = Path(expanded)
    if path.exists():
        return path
    return None


def _find_windows_start_menu_shortcut(app_name: str) -> Optional[Path]:
    query = _normalize_match_ascii(app_name)
    tokens = [token for token in query.split() if token]
    if not tokens:
        return None

    roots = []
    program_data = os.getenv('ProgramData', '').strip()
    app_data = os.getenv('APPDATA', '').strip()
    if program_data:
        roots.append(Path(program_data) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs')
    if app_data:
        roots.append(Path(app_data) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs')

    candidates: List[Tuple[int, Path]] = []
    for root in roots:
        if not root.exists():
            continue
        try:
            for shortcut_path in root.rglob('*.lnk'):
                score = _score_app_name_match(shortcut_path.stem, query, tokens)
                if score >= 18:
                    candidates.append((score, shortcut_path))
        except Exception:
            continue

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _find_windows_app_paths_executable(app_name: str) -> Optional[Path]:
    if os.name != 'nt':
        return None

    query = _normalize_match_ascii(app_name)
    tokens = [token for token in query.split() if token]
    if not tokens:
        return None

    try:
        import winreg
    except Exception:
        return None

    registry_locations = [
        (winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\App Paths'),
        (winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows\CurrentVersion\App Paths'),
        (winreg.HKEY_LOCAL_MACHINE, r'Software\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths'),
    ]

    candidates: List[Tuple[int, Path]] = []
    for hive, key_path in registry_locations:
        try:
            with winreg.OpenKey(hive, key_path) as app_paths_key:
                index = 0
                while True:
                    try:
                        sub_key_name = winreg.EnumKey(app_paths_key, index)
                    except OSError:
                        break
                    index += 1

                    try:
                        with winreg.OpenKey(app_paths_key, sub_key_name) as sub_key:
                            default_value, _ = winreg.QueryValueEx(sub_key, None)
                    except OSError:
                        continue

                    executable_path = _extract_executable_path_from_command(str(default_value or ''))
                    if not executable_path:
                        continue

                    alias_name = Path(sub_key_name).stem
                    score = max(
                        _score_app_name_match(alias_name, query, tokens),
                        _score_app_name_match(executable_path.stem, query, tokens),
                    )
                    if score >= 18:
                        candidates.append((score, executable_path))
        except OSError:
            continue

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _load_windowsapps_alias_index() -> Dict[str, Path]:
    if os.name != 'nt':
        return {}

    now = time.time()
    with _APP_LAUNCHER_CACHE_LOCK:
        cached_time, cached_index = _APP_LAUNCHER_CACHE
        if cached_index and (now - cached_time) < APP_LAUNCHER_CACHE_TTL_SECONDS:
            return dict(cached_index)

    alias_dir = Path(os.getenv('LOCALAPPDATA', '').strip()) / 'Microsoft' / 'WindowsApps'
    index: Dict[str, Path] = {}
    if alias_dir.exists():
        try:
            for executable in alias_dir.glob('*.exe'):
                alias_key = _normalize_match_ascii(executable.stem)
                if alias_key and alias_key not in index:
                    index[alias_key] = executable
        except Exception:
            index = {}

    with _APP_LAUNCHER_CACHE_LOCK:
        _APP_LAUNCHER_CACHE = (now, dict(index))
    return index


def _find_windowsapps_alias_executable(app_name: str) -> Optional[Path]:
    query = _normalize_match_ascii(app_name)
    tokens = [token for token in query.split() if token]
    if not tokens:
        return None

    alias_index = _load_windowsapps_alias_index()
    if not alias_index:
        return None

    candidates: List[Tuple[int, Path]] = []
    for alias_key, alias_path in alias_index.items():
        score = _score_app_name_match(alias_key, query, tokens)
        if score >= 18:
            candidates.append((score, alias_path))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _build_app_name_candidates(raw_target: str) -> List[str]:
    original = str(raw_target or '').strip()
    if not original:
        return []

    normalized_tokens = _normalize_match_ascii(original).split()
    trailing_noise = {'nhe', 'nha', 'voi', 'giup', 'toi', 'dum', 'di', 'duoc', 'khong'}
    while normalized_tokens and normalized_tokens[-1] in trailing_noise:
        normalized_tokens.pop()

    if len(normalized_tokens) >= 2 and normalized_tokens[0] == 'ung' and normalized_tokens[1] == 'dung':
        normalized_tokens = normalized_tokens[2:]
    elif normalized_tokens and normalized_tokens[0] in {'app', 'application'}:
        normalized_tokens = normalized_tokens[1:]

    normalized_core = ' '.join(normalized_tokens).strip()

    candidates = [original]
    if normalized_core:
        candidates.append(normalized_core)
    if len(normalized_tokens) >= 2:
        candidates.append(' '.join(normalized_tokens[:2]))
    if normalized_tokens:
        candidates.append(normalized_tokens[0])
        candidates.append(normalized_tokens[-1])

    unique = []
    seen = set()
    for candidate in candidates:
        item = str(candidate).strip()
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _open_windows_application(app_name: str) -> str:
    target = str(app_name or '').strip()
    if not target:
        raise ValueError('Thiếu tên ứng dụng để mở.')

    if os.name != 'nt':
        raise OSError('Hành động OPEN_APP hiện chỉ hỗ trợ trên Windows.')

    if target.lower().startswith(('http://', 'https://')):
        os.startfile(target)  # type: ignore[attr-defined]
        return target

    expanded = os.path.expandvars(os.path.expanduser(target))
    direct_path = Path(expanded)
    if direct_path.exists():
        os.startfile(str(direct_path))  # type: ignore[attr-defined]
        return direct_path.name or target

    raw_candidates = _build_app_name_candidates(target)
    candidate_names = []
    for raw_candidate in raw_candidates:
        candidate_names.append(raw_candidate)
        if not raw_candidate.lower().endswith('.exe'):
            candidate_names.append(f'{raw_candidate}.exe')

    for candidate in candidate_names:
        found_path = shutil.which(candidate)
        if found_path:
            os.startfile(found_path)  # type: ignore[attr-defined]
            return Path(found_path).name

    app_paths_executable = _find_windows_app_paths_executable(target)
    if app_paths_executable:
        os.startfile(str(app_paths_executable))  # type: ignore[attr-defined]
        return app_paths_executable.name

    shortcut = _find_windows_start_menu_shortcut(target)
    if shortcut:
        os.startfile(str(shortcut))  # type: ignore[attr-defined]
        return shortcut.name

    windowsapps_alias = _find_windowsapps_alias_executable(target)
    if windowsapps_alias:
        os.startfile(str(windowsapps_alias))  # type: ignore[attr-defined]
        return windowsapps_alias.name

    raise FileNotFoundError('Không tìm thấy ứng dụng cần mở.')

def _list_running_windows_processes() -> List[Tuple[str, int]]:
    if os.name != 'nt':
        return []

    try:
        result = subprocess.run(
            ['tasklist', '/fo', 'csv', '/nh'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            check=False,
            timeout=8,
        )
    except Exception:
        return []

    if result.returncode != 0:
        return []

    rows: List[Tuple[str, int]] = []
    reader = csv.reader(result.stdout.splitlines())
    for row in reader:
        if len(row) < 2:
            continue
        image_name = str(row[0] or '').strip()
        pid_text = str(row[1] or '').strip()
        if not image_name or not pid_text.isdigit():
            continue
        rows.append((image_name, int(pid_text)))
    return rows


def _close_windows_application(app_name: str) -> str:
    target = str(app_name or '').strip()
    if not target:
        raise ValueError('Thiếu tên ứng dụng để đóng.')

    if os.name != 'nt':
        raise OSError('Hành động CLOSE_APP hiện chỉ hỗ trợ trên Windows.')

    running_processes = _list_running_windows_processes()
    if not running_processes:
        raise RuntimeError('Không đọc được danh sách tiến trình đang chạy.')

    raw_candidates = _build_app_name_candidates(target)
    target_variants: List[str] = []
    if raw_candidates:
        target_variants.extend(raw_candidates)
    target_variants.append(Path(target).stem)
    target_variants.append(target)

    scored_processes: List[Tuple[int, str, int]] = []
    for image_name, pid in running_processes:
        image_base = Path(image_name).stem
        best_score = -1
        for variant in target_variants:
            query = _normalize_match_ascii(variant)
            tokens = [token for token in query.split() if token]
            if not tokens:
                continue
            score = _score_app_name_match(image_base, query, tokens)
            if score > best_score:
                best_score = score
        if best_score >= 18:
            scored_processes.append((best_score, image_name, pid))

    if not scored_processes:
        raise FileNotFoundError(f'Không tìm thấy tiến trình đang chạy cho ứng dụng: {target}')

    scored_processes.sort(key=lambda item: item[0], reverse=True)
    top_score = scored_processes[0][0]
    matched = [(image_name, pid) for score, image_name, pid in scored_processes if score >= max(8, top_score - 6)]
    if not matched:
        matched = [(scored_processes[0][1], scored_processes[0][2])]

    taskkill_command = ['taskkill', '/T', '/F']
    for _, pid in matched:
        taskkill_command.extend(['/PID', str(pid)])

    result = subprocess.run(
        taskkill_command,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore',
        check=False,
        timeout=10,
    )
    if result.returncode != 0:
        stderr = (result.stderr or '').strip()
        stdout = (result.stdout or '').strip()
        detail = stderr or stdout or 'taskkill trả về mã lỗi.'
        raise RuntimeError(f'Không đóng được ứng dụng "{target}": {detail}')

    image_names = sorted({image_name for image_name, _ in matched})
    return f'Đã đóng ứng dụng: {", ".join(image_names)} ({len(matched)} tiến trình).'


def _execute_computer_control_action(action_text: str, prompt: str, prompt_tail: str) -> str:
    raw_action = str(action_text or '').strip()
    if not raw_action:
        raise ValueError('Hành động trống.')

    parts = [part.strip() for part in raw_action.split('|')]
    command = parts[0].upper()

    if command in {'SCAN_DESKTOP_CLOCK', 'CHECK_DESKTOP_CLOCK', 'SCANDESKTOPCLOCK', 'CHECKDESKTOPCLOCK'}:
        return _scan_desktop_clock_text()

    if command in {'OPEN_APP', 'OPENAPP', 'LAUNCH_APP', 'RUN_APP', 'OPEN_APPLICATION'}:
        if len(parts) < 2:
            raise ValueError(f'Hành động {command} cần tên ứng dụng.')
        app_target = _render_control_value(parts[1], prompt, prompt_tail)
        opened_target = _open_windows_application(app_target)
        return f'Đã mở ứng dụng: {opened_target}'

    if command in {'CLOSE_APP', 'CLOSEAPP', 'KILL_APP', 'STOP_APP', 'TERMINATE_APP', 'CLOSE_APPLICATION'}:
        if len(parts) < 2:
            raise ValueError(f'Hành động {command} cần tên ứng dụng.')
        app_target = _render_control_value(parts[1], prompt, prompt_tail)
        return _close_windows_application(app_target)

    if command in {'OPEN_FILE', 'READ_FILE', 'OPEN', 'READ'}:
        if len(parts) < 2:
            raise ValueError(f'Hành động {command} cần 1 tham số đường dẫn.')
        file_path = _resolve_control_path(_render_control_value(parts[1], prompt, prompt_tail))
        if not file_path.exists():
            raise FileNotFoundError('Không tìm thấy tệp hoặc thư mục.')
        if file_path.is_dir():
            return _list_dir_preview(file_path)
        return _read_file_preview(file_path)

    if command in {'LIST_DIR', 'LS'}:
        if len(parts) < 2:
            raise ValueError(f'Hành động {command} cần 1 tham số đường dẫn.')
        dir_path = _resolve_control_path(_render_control_value(parts[1], prompt, prompt_tail))
        if not dir_path.exists():
            raise FileNotFoundError('Không tìm thấy thư mục.')
        if not dir_path.is_dir():
            raise NotADirectoryError('Mục đã chọn không phải thư mục.')
        return _list_dir_preview(dir_path)

    if command in {'WRITE_FILE', 'WRITE'}:
        if len(parts) < 3:
            raise ValueError(f'Hành động {command} cần đường dẫn và nội dung.')
        file_path = _resolve_control_path(_render_control_value(parts[1], prompt, prompt_tail))
        content_raw = '|'.join(parts[2:])
        content = _render_control_value(content_raw, prompt, prompt_tail)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
        return f'Đã ghi tệp ({len(content)} ký tự).'

    if command in {'APPEND_FILE', 'APPEND'}:
        if len(parts) < 3:
            raise ValueError(f'Hành động {command} cần đường dẫn và nội dung.')
        file_path = _resolve_control_path(_render_control_value(parts[1], prompt, prompt_tail))
        content_raw = '|'.join(parts[2:])
        content = _render_control_value(content_raw, prompt, prompt_tail)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open('a', encoding='utf-8') as handler:
            handler.write(content)
        return f'Đã thêm vào tệp ({len(content)} ký tự).'

    if command in {'CREATE_FILE', 'TOUCH_FILE'}:
        if len(parts) < 2:
            raise ValueError(f'Hành động {command} cần 1 tham số đường dẫn.')
        file_path = _resolve_control_path(_render_control_value(parts[1], prompt, prompt_tail))
        content_raw = '|'.join(parts[2:]) if len(parts) > 2 else ''
        content = _render_control_value(content_raw, prompt, prompt_tail)
        if file_path.exists():
            return 'Tệp đã tồn tại.'
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
        return 'Đã tạo tệp.'

    if command in {'CREATE_DIR', 'MKDIR', 'CREATE_FOLDER'}:
        if len(parts) < 2:
            raise ValueError(f'Hành động {command} cần 1 tham số đường dẫn.')
        dir_path = _resolve_control_path(_render_control_value(parts[1], prompt, prompt_tail))
        dir_path.mkdir(parents=True, exist_ok=True)
        return 'Đã tạo thư mục.'

    if command in {'DELETE_FILE', 'REMOVE_FILE'}:
        if len(parts) < 2:
            raise ValueError(f'Hành động {command} cần 1 tham số đường dẫn.')
        file_path = _resolve_control_path(_render_control_value(parts[1], prompt, prompt_tail))
        _ensure_deletion_allowed(file_path)
        if not file_path.exists():
            return 'Không tìm thấy tệp để xóa.'
        if file_path.is_dir():
            raise IsADirectoryError('Đường dẫn là thư mục, hãy dùng DELETE_DIR.')
        file_path.unlink()
        return 'Đã xóa tệp.'

    if command in {'DELETE_DIR', 'RMDIR', 'REMOVE_DIR'}:
        if len(parts) < 2:
            raise ValueError(f'Hành động {command} cần 1 tham số đường dẫn.')
        dir_path = _resolve_control_path(_render_control_value(parts[1], prompt, prompt_tail))
        _ensure_deletion_allowed(dir_path)
        if not dir_path.exists():
            return 'Không tìm thấy thư mục để xóa.'
        if not dir_path.is_dir():
            raise NotADirectoryError('Mục đã chọn không phải thư mục.')
        shutil.rmtree(dir_path)
        return 'Đã xóa thư mục.'

    if command in {'DELETE_PATH', 'DELETE', 'REMOVE'}:
        if len(parts) < 2:
            raise ValueError(f'Hành động {command} cần 1 tham số đường dẫn.')
        path = _resolve_control_path(_render_control_value(parts[1], prompt, prompt_tail))
        _ensure_deletion_allowed(path)
        if not path.exists():
            return 'Không tìm thấy mục để xóa.'
        if path.is_dir():
            shutil.rmtree(path)
            return 'Đã xóa thư mục.'
        path.unlink()
        return 'Đã xóa tệp.'

    raise ValueError(f'Hành động không hỗ trợ: {command}')


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
            prompt_tail_candidate = _extract_prompt_tail(prompt_for_control, trigger)
            actions_candidate = [str(action) for action in rule.get('actions', [])]
            if not prompt_tail_candidate:
                requires_tail = any(
                    action.upper().startswith(('OPEN_APP|', 'CLOSE_APP|', 'KILL_APP|', 'STOP_APP|', 'TERMINATE_APP|'))
                    and '{REST}' in action
                    for action in actions_candidate
                )
                if requires_tail:
                    continue
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
        except Exception:
            action_logs.append(f'{idx}. Không thực hiện được lệnh này.')
            break

    if not action_logs:
        return None
    return f'Đã thực thi tập lệnh train: "{trigger_display}"\n' + '\n'.join(action_logs)


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
    endings = ['há»c', 'viĂªn', 'thuáº­t', 'lĂ½', 'vÄƒn', 'sá»­', 'Ä‘áº¡o', 'Ä‘á»©c', 'hĂ³a', 'phĂ¡p', 'trĂ¬nh']
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
    starters = ['há»c sinh', 'cĂ´ng nghá»‡', 'Ă¢m nháº¡c', 'hĂ²a bĂ¬nh', 'mĂ´i trÆ°á»ng']
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
        'Luáº­t ná»‘i tá»«: tá»« cá»§a báº¡n pháº£i báº¯t Ä‘áº§u báº±ng tiáº¿ng cuá»‘i cá»§a tá»« trÆ°á»›c Ä‘Ă³, '
        'khĂ´ng láº·p láº¡i tá»« Ä‘Ă£ dĂ¹ng. '
        'GĂµ "chÆ¡i ná»‘i tá»«" Ä‘á»ƒ báº¯t Ä‘áº§u vĂ  "dá»«ng ná»‘i tá»«" Ä‘á»ƒ thoĂ¡t.'
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
            return 'ÄĂ£ dá»«ng trĂ² chÆ¡i ná»‘i tá»«. Khi muá»‘n chÆ¡i láº¡i, báº¡n chá»‰ cáº§n gĂµ "chÆ¡i ná»‘i tá»«".'
        return 'Hiá»‡n táº¡i chÆ°a cĂ³ vĂ¡n ná»‘i tá»« nĂ o Ä‘ang cháº¡y.'

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
            f'Báº¯t Ä‘áº§u nhĂ©. MĂ¬nh ra trÆ°á»›c: "{seed_phrase}". '
            f'LÆ°á»£t báº¡n, hĂ£y ná»‘i báº±ng tá»« báº¯t Ä‘áº§u vá»›i "{next_display}".'
        )

    if not state.get('active'):
        return None

    user_phrase = _normalize_word_chain_phrase(prompt)
    user_parts = user_phrase.split()
    if not user_parts:
        return 'Báº¡n gá»­i má»™t tá»« hoáº·c cá»¥m ngáº¯n Ä‘á»ƒ ná»‘i tá»« nhĂ©.'

    if len(user_parts) > 4:
        return 'Tá»« ná»‘i nĂªn ngáº¯n gá»n (1-4 tiáº¿ng) Ä‘á»ƒ mĂ¬nh kiá»ƒm tra chĂ­nh xĂ¡c hÆ¡n.'

    expected_key = str(state.get('expected', '')).strip()
    expected_display = str(state.get('expected_display', '')).strip() or expected_key
    first_key = _word_chain_first_key(user_phrase)

    if expected_key and first_key != expected_key:
        return f'ChÆ°a há»£p lá»‡. Tá»« cá»§a báº¡n pháº£i báº¯t Ä‘áº§u báº±ng "{expected_display}".'

    used_keys = set(str(item).strip().lower() for item in state.get('used', []))
    user_key = _word_chain_phrase_key(user_phrase)
    if user_key in used_keys:
        return 'Tá»« nĂ y Ä‘Ă£ dĂ¹ng rá»“i, báº¡n thá»­ tá»« khĂ¡c nhĂ©.'

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
            return f'"{user_phrase}" há»£p lá»‡. MĂ¬nh bĂ­ tá»« rá»“i, báº¡n tháº¯ng vĂ¡n nĂ y.'
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
        f'Hop le. Minh noi: "{bot_phrase}". '
        f'Luot ban, bat dau bang "{next_display}".'
    )



def _rule_based_answer(prompt: str) -> Optional[str]:
    clean = _normalize_match(prompt)
    if not clean:
        return None

    now = datetime.now()

    if 'hom nay' in clean and ('ngay bao nhieu' in clean or 'ngay may' in clean):
        return f"Hom nay la ngay {now.strftime('%d/%m/%Y')}."

    if 'bay gio may gio' in clean or 'may gio' in clean or 'gio hien tai' in clean:
        return f"Bay gio la {now.strftime('%H:%M')} ngay {now.strftime('%d/%m/%Y')}."

    if clean in {'hello', 'hi'}:
        return 'Hello. I am ready to help you.'
    if clean in {'xin chao', 'chao'}:
        return 'Chao ban. Minh dang san sang ho tro ban.'

    is_china_marker = any(marker in clean for marker in ('trung quoc', 'trung hoa', 'china'))
    if 'noi chien trung quoc' in clean or 'noi chien trung hoa' in clean or (
        is_china_marker and ('quoc dan dang' in clean or 'dang cong san' in clean or 'noi chien' in clean)
    ):
        if 'ai lanh dao' in clean or 'lanh dao' in clean:
            return (
                'Trong Noi chien Trung Quoc, phe Cong san do Mao Trach Dong lanh dao. '
                'Phe Quoc dan dang do Tuong Gioi Thach lanh dao.'
            )
        return (
            'Noi chien Trung Quoc (1927-1949, gian doan thoi ky khang Nhat) dien ra giua '
            'Dang Cong san Trung Quoc va Quoc dan dang. Ket qua la phe Cong san thang loi, '
            'thanh lap nuoc Cong hoa Nhan dan Trung Hoa nam 1949.'
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
            'Trong Noi chien Trung Quoc, phe Cong san do Mao Trach Dong lanh dao, '
            'con phe Quoc dan dang do Tuong Gioi Thach lanh dao.'
        )

    if ('cuoc chien do' in clean_prompt and 'dien ra' in clean_prompt) or 'dien ra nhu the nao' in clean_prompt:
        return (
            'Noi chien Trung Quoc dien ra theo nhieu giai doan tu 1927 den 1949 '
            '(co gian doan thoi ky khang Nhat 1937-1945), giua Quoc dan dang va '
            'Dang Cong san Trung Quoc; ket cuc la phe Cong san thang va lap nuoc '
            'Cong hoa Nhan dan Trung Hoa nam 1949.'
        )

    return None



def _is_low_quality_answer(answer: str) -> bool:
    clean = (answer or '').strip().lower()
    if len(clean) < 5:
        return True

    normalized = re.sub(r'[^a-z0-9\s]', ' ', clean)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    if not normalized:
        return True

    trivial = {
        'aipa',
        'ai',
        'tro ly',
        'troly',
        'assistant',
        'ok',
        'vang',
        'da',
        'roi',
    }
    if normalized in trivial:
        return True

    tokens = [t for t in normalized.split(' ') if t]
    filler_tokens = {'aipa', 'ai', 'assistant', 'tro', 'ly', 'ok', 'vang', 'da', 'roi'}
    if tokens and len(tokens) <= 3 and all(token in filler_tokens for token in tokens):
        return True

    normalized_ascii = _normalize_match_ascii(answer)
    if any(
        marker in normalized_ascii for marker in (
            'da thuc thi tap lenh train',
            'thc thi tp lnh train',
            'da mo ung dung',
            'm ng dng',
        )
    ):
        return True

    if len(tokens) >= 14:
        unique_ratio = len(set(tokens)) / max(1, len(tokens))
        if unique_ratio < 0.32:
            return True

    return False


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


def _repair_likely_mojibake(text: str) -> str:
    raw = str(text or '')
    if not raw:
        return ''

    mojibake_markers = ('Ã', 'Ä', 'Ă', 'Â', 'á»', 'áº', 'â€', 'â€™')
    if not any(marker in raw for marker in mojibake_markers):
        return raw

    def _badness(value: str) -> int:
        return sum(value.count(marker) for marker in mojibake_markers)

    for legacy_codec in ('latin-1', 'cp1252'):
        try:
            repaired = raw.encode(legacy_codec).decode('utf-8')
        except Exception:
            continue
        if repaired and _badness(repaired) < _badness(raw):
            return repaired

    return raw


def _postprocess_answer(answer: str, max_len: int = 1400) -> str:
    clean = (answer or '').strip()
    if not clean:
        return ''

    clean = clean.replace('**', '').replace('`', '')
    clean = _repair_likely_mojibake(clean)
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
                'Trong Noi chien Trung Quoc, phe Cong san do Mao Trach Dong lanh dao, '
                'con phe Quoc dan dang do Tuong Gioi Thach lanh dao.'
            )
        return (
            'Noi chien Trung Quoc dien ra giua Dang Cong san Trung Quoc va Quoc dan dang '
            'trong giai doan 1927-1949 (gian doan thoi ky khang Nhat).',
        )

    return answer


app = FastAPI(title='AIPA Controll AI Service', version='1.1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://localhost:8080',
        'http://127.0.0.1:8080',
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
        'knowledge_size': knowledge_store.knowledge_size(),
        'memory_sessions': conversation_store.session_count(),
    }


@app.post('/api/train')
def train_qa(request: TrainRequest):
    knowledge_store.add_pair(request.question, request.answer)
    return {
        'message': 'Đã cập nhật dữ liệu train thành công.',
        'knowledge_size': knowledge_store.knowledge_size(),
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

    if should_lookup_web:
        if not web_search_service.active:
            web_notice = ''
        elif not web_search_service.google_ready:
            web_notice = ''
        else:
            web_results = web_search_service.search_google(request.prompt, limit=3)
            if web_results:
                web_answer = _postprocess_answer(_build_web_answer(web_results), max_len=1800)
                conversation_store.append_exchange(session_id, request.prompt, web_answer)
                search_model = 'google_forced' if force_google_lookup else 'google_search'
                return ChatResponse(answer=web_answer, source='web', model=search_model)
            web_notice = 'Hiện tại mình chưa thể tra cứu web. Bạn thử lại sau ít phút.'

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

    prompt_for_model = _apply_language_instruction(prompt_for_model, request.prompt)

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

    if not web_results and WEB_SEARCH_ENABLED and web_search_service.google_ready and not should_lookup_web:
        # Last-resort web lookup when all model providers are unavailable.
        rescue_results = web_search_service.search_google(request.prompt, limit=3)
        if rescue_results:
            web_results = rescue_results

    if web_results:
        fallback_answer = _build_web_answer(web_results)
    elif should_lookup_web and web_notice:
        fallback_answer = web_notice
    else:
        fallback_answer = (
            'Mình đã nhận câu hỏi nhưng hệ thống AI đang bận khởi động hoặc tạm thời quá tải. '
            'Bạn thử lại sau ít phút, hoặc đặt câu hỏi cụ thể hơn để mình trả lời tốt hơn.'
        )
    fallback_answer = _postprocess_answer(fallback_answer, max_len=1600)
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



