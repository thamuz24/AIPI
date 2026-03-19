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
WEB_SEARCH_SOURCE_LIMIT = 1
WEB_SEARCH_WORD_LIMIT = 250
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
COMPUTER_CONTROL_DOC_FILE = BASE_DIR / 'docs' / 'COMPUTER_CONTROL_PROMPTS.md'
REQUIREMENTS_FILE = BASE_DIR / 'requirements-chat.txt'
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
CONTROL_DESKTOP_ROOT = Path(
    os.getenv(
        'AIPA_CONTROL_DESKTOP_ROOT',
        str(Path(os.path.expanduser('~')) / 'Desktop'),
    )
).resolve()
CONTROL_READ_PREVIEW_LIMIT = int(os.getenv('AIPA_CONTROL_READ_PREVIEW_LIMIT', '2500'))
CONTROL_LIST_LIMIT = int(os.getenv('AIPA_CONTROL_LIST_LIMIT', '50'))
COMPUTER_CONTROL_BUILD_TAG = os.getenv('AIPA_COMPUTER_CONTROL_BUILD_TAG', 'computer-control-2026-03-12a').strip()
try:
    CONTROL_GRID_ROWS = max(1, int(os.getenv('AIPA_CONTROL_GRID_ROWS', '6')))
except ValueError:
    CONTROL_GRID_ROWS = 6
try:
    CONTROL_GRID_COLS = max(1, int(os.getenv('AIPA_CONTROL_GRID_COLS', '6')))
except ValueError:
    CONTROL_GRID_COLS = 6
try:
    KNOWLEDGE_VECTOR_DIM = max(64, int(os.getenv('AIPA_KNOWLEDGE_VECTOR_DIM', '256')))
except ValueError:
    KNOWLEDGE_VECTOR_DIM = 256
try:
    KNOWLEDGE_MATCH_THRESHOLD = float(os.getenv('AIPA_KNOWLEDGE_MATCH_THRESHOLD', '0.68'))
except ValueError:
    KNOWLEDGE_MATCH_THRESHOLD = 0.68

DEFAULT_WEB_SEARCH_INTENT_KEYWORDS = [
    'tìm trên google',
    'tìm trên mạng',
    'tìm kiếm',
    'tra cứu',
    'tìm nguồn',
    'nguồn tham khảo',
    'cho mình nguồn',
    'cho xin nguồn',
    'trích dẫn nguồn',
    'đính kèm link',
    'gửi link',
    'tài liệu',
    'tài liệu tham khảo',
    'tài liệu học',
    'tài liệu chính thức',
    'tài liệu hướng dẫn',
    'paper',
    'pdf',
    'documentation',
    'tài liệu api',
    'api docs',
    'wiki',
    'wikipedia',
    'fact check',
    'kiểm chứng',
]

DEFAULT_WEB_SEARCH_FRESHNESS_KEYWORDS = [
    'hôm nay',
    'mới nhất',
    'tin tức',
    'cập nhật',
    'giá',
    'giá vàng',
    'giá usd',
    'tỷ giá',
    'thời tiết',
    'lịch thi đấu',
    'kết quả trận',
]

DEFAULT_WEB_SEARCH_FORCED_KEYWORDS = [
    'làm thế nào',
    'bạn có biết',
    'vì sao',
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
    'ràng buộc',
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
        self.seed_file = COMMON_QA_SEED_FILE
        self.seed_dir = KEYWORD_TRAIN_DIR
        self.lock = threading.Lock()
        self._pairs = self._load_pairs()
        self._seed_pairs: List[dict] = []
        self._seed_primary_pairs: List[dict] = []
        self._seed_signature = ''
        self._refresh_seed_pairs(force=True)

    def _load_pairs(self):
        if not self.file_path.exists():
            return []
        try:
            data = json.loads(self.file_path.read_text(encoding='utf-8'))
            if isinstance(data, list):
                repaired = []
                changed = False
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    question = _repair_mojibake_text(str(item.get('question', '')))
                    answer = _repair_mojibake_text(str(item.get('answer', '')))
                    if question != item.get('question') or answer != item.get('answer'):
                        changed = True
                    repaired.append({'question': question, 'answer': answer})
                if changed:
                    try:
                        self.file_path.write_text(
                            json.dumps(repaired, ensure_ascii=False, indent=2),
                            encoding='utf-8',
                        )
                    except Exception:
                        pass
                return repaired
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
        primary_pairs = self._load_seed_pairs([self.seed_file]) if self.seed_file.exists() else []
        other_files = [file_path for file_path in files if file_path != self.seed_file]
        other_pairs = self._load_seed_pairs(other_files)
        self._seed_primary_pairs = primary_pairs
        self._seed_pairs = primary_pairs + other_pairs
        self._seed_signature = signature

    def _combined_pairs(self):
        self._refresh_seed_pairs()
        combined = []
        seen = set()

        for item in self._seed_pairs:
            q = self._normalize(item.get('question', ''))
            if not q:
                continue
            if q in seen:
                continue
            seen.add(q)
            combined.append(item)

        for item in self._pairs:
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

    def _find_answer_in_pairs(self, question: str, pairs: List[dict], threshold: float) -> Optional[str]:
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

        if best_score >= threshold:
            return best_answer
        return None

    def find_answer(self, question: str) -> Optional[str]:
        self._refresh_seed_pairs()
        prioritized_answer = self._find_answer_in_pairs(
            question,
            self._seed_primary_pairs,
            threshold=max(0.60, KNOWLEDGE_MATCH_THRESHOLD - 0.06),
        )
        if prioritized_answer:
            return prioritized_answer

        return self._find_answer_in_pairs(question, self._combined_pairs(), threshold=KNOWLEDGE_MATCH_THRESHOLD)


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
        changed = False
        for key, value in sessions.items():
            if not isinstance(value, dict):
                continue
            sid = self.normalize_session_id(str(key))
            messages = value.get('messages', [])
            facts = value.get('facts', [])
            raw_word_chain = value.get('word_chain', {})
            repaired_messages = []
            for item in messages if isinstance(messages, list) else []:
                if not isinstance(item, dict):
                    continue
                sender = str(item.get('sender', '')).strip() or 'bot'
                text = _repair_mojibake_text(str(item.get('text', '')))
                at = str(item.get('at', '')).strip()
                if text != item.get('text'):
                    changed = True
                repaired_messages.append({'sender': sender, 'text': text, 'at': at})
            repaired_facts = []
            for item in facts if isinstance(facts, list) else []:
                fact = _repair_mojibake_text(str(item).strip())
                if fact and fact != str(item).strip():
                    changed = True
                if fact:
                    repaired_facts.append(fact)
            sanitized[sid] = {
                'messages': repaired_messages,
                'facts': repaired_facts,
                'word_chain': self._sanitize_word_chain_state(raw_word_chain),
                'updated_at': str(value.get('updated_at', '')),
            }
        if changed:
            try:
                payload = {'sessions': sanitized}
                self.file_path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding='utf-8',
                )
            except Exception:
                pass
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
            ('toi ten la ', 'Tên người dùng là {}.'),
            ('minh ten la ', 'Tên người dùng là {}.'),
            ('ten toi la ', 'Tên người dùng là {}.'),
            ('my name is ', 'Tên người dùng là {}.'),
            ('toi la ', 'Người dùng là {}.'),
            ('minh la ', 'Người dùng là {}.'),
            ('i am ', 'Người dùng là {}.'),
            ('toi thich ', 'Sở thích của người dùng: {}.'),
            ('minh thich ', 'Sở thích của người dùng: {}.'),
            ('i like ', 'Sở thích của người dùng: {}.'),
            ('muc tieu cua toi la ', 'Mục tiêu của người dùng: {}.'),
            ('toi dang lam ', 'Người dùng đang làm: {}.'),
            ('minh dang lam ', 'Người dùng đang làm: {}.'),
        ]

        for prefix, template in direct_patterns:
            if clean.startswith(prefix):
                value = cls._shorten_fact_value(clean[len(prefix):])
                if 2 <= len(value) <= 80:
                    facts.append(template.format(value))

        if len(clean) <= 80 and clean.startswith('toi o ') and len(clean) > len('toi o '):
            location = cls._shorten_fact_value(clean[len('toi o '):])
            if location:
                facts.append(f'Người dùng ở {location}.')

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

    def _search_with_serper(self, prompt: str, limit: int = 1) -> List[dict]:
        self.last_error = ''
        if not self.serper_api_key:
            self.last_error = 'Chưa cấu hình SERPER_API_KEY.'
            return []

        search_limit = max(1, min(limit, WEB_SEARCH_SOURCE_LIMIT))
        payload = json.dumps(
            {
                'q': prompt,
                'num': search_limit,
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
        for item in organic[:search_limit]:
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

    def _search_with_serpapi(self, prompt: str, limit: int = 1) -> List[dict]:
        self.last_error = ''
        if not self.serpapi_api_key:
            self.last_error = 'Chưa cấu hình SERPAPI_API_KEY.'
            return []

        search_limit = max(1, min(limit, WEB_SEARCH_SOURCE_LIMIT))
        params = {
            'engine': 'google',
            'q': prompt,
            'hl': 'vi',
            'gl': 'vn',
            'num': str(search_limit),
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
        for item in organic[:search_limit]:
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
    def _search_with_wikipedia(prompt: str, limit: int = 1) -> List[dict]:
        search_limit = max(1, min(limit, WEB_SEARCH_SOURCE_LIMIT))
        encoded = urlparse.quote(prompt)
        url = (
            'https://vi.wikipedia.org/w/api.php?action=opensearch'
            f'&search={encoded}&limit={search_limit}&namespace=0&format=json'
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
        for idx, title in enumerate(titles[:search_limit]):
            t = str(title).strip()
            s = str(snippets[idx]).strip() if idx < len(snippets) else ''
            u = str(urls[idx]).strip() if idx < len(urls) else ''
            if t and (s or u):
                results.append({'title': t, 'snippet': s, 'url': u})
        return results

    def search_google(self, prompt: str, limit: int = 1) -> List[dict]:
        if not self.active:
            return []
        search_limit = max(1, min(limit, WEB_SEARCH_SOURCE_LIMIT))
        cached = self._cache_get(prompt)
        if cached:
            self.last_error = ''
            return cached[:search_limit]

        # Prioritize SerpApi because many users provide SerpApi key for Google search.
        results = self._search_with_serpapi(prompt, limit=search_limit) if self.serpapi_api_key else []
        if not results and self.serper_api_key:
            results = self._search_with_serper(prompt, limit=search_limit)

        if results:
            self._cache_set(prompt, results)
        return results

    def search(self, prompt: str, limit: int = 1) -> List[dict]:
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
        'co hai',
        'tac hai',
        'nguy hiem',
        'khi nao',
        'nam nao',
        'bao nhieu',
        'tu bao gio',
        'khoi sinh',
        'khai sinh',
        'thanh lap',
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


def _truncate_by_words(text: str, max_words: int) -> str:
    clean = str(text or '').strip()
    if not clean:
        return ''

    words = clean.split()
    if len(words) <= max_words:
        return clean
    return ' '.join(words[:max_words]).strip() + '...'


def _first_sentence(text: str) -> str:
    if not text:
        return ''
    for sep in ('.', '!', '?', '\n'):
        if sep in text:
            return text.split(sep, 1)[0].strip()
    return text.strip()


def _extract_short_answer(prompt: str, content: str, title: str = '') -> str:
    clean_prompt = _normalize_match_ascii(prompt)
    clean_content = (content or '').strip()
    if not clean_content:
        return title.strip()

    if 'thu do' in clean_prompt:
        match = re.search(r'thủ đô\s+([A-ZÀ-Ỹa-zà-ỹ][^.,;:\n]+)', clean_content, flags=re.IGNORECASE)
        if match:
            return f'Thủ đô: {match.group(1).strip()}.'

    if 'o dau' in clean_prompt:
        for pattern in (
            r'nằm ở\s+([^.,;\n]+)',
            r'thuộc\s+([^.,;\n]+)',
            r'ở\s+([^.,;\n]+)',
            r'tại\s+([^.,;\n]+)',
        ):
            match = re.search(pattern, clean_content, flags=re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                return f'Địa điểm: {location}.'
        return _first_sentence(clean_content)

    if any(marker in clean_prompt for marker in ('la ai', 'la gi', 'nuoc nao', 'la nuoc nao', 'co gi')):
        return _first_sentence(clean_content)

    return _first_sentence(clean_content)


def _build_web_answer(prompt: str, results: List[dict]) -> str:
    if not results:
        return 'Không tìm thấy thông tin phù hợp.'

    item = results[0]
    title = str(item.get('title', '')).strip()
    snippet = str(item.get('snippet', '')).strip()

    base = ' '.join(part for part in (title, snippet) if part).strip()
    content = base or 'Không có nội dung tóm tắt.'
    content = _truncate_by_words(content, WEB_SEARCH_WORD_LIMIT - 30)

    short_answer = _extract_short_answer(prompt, content, title)
    lines = []
    if short_answer:
        lines.append(f'Trả lời ngắn gọn: {short_answer}')
    lines.append(f'Tóm tắt: {content}')

    return _truncate_by_words('\n'.join(lines), WEB_SEARCH_WORD_LIMIT)


def _search_web_answer(prompt: str) -> Optional[str]:
    if not WEB_SEARCH_ENABLED or not web_search_service.active or not web_search_service.google_ready:
        return None
    try:
        results = web_search_service.search_google(prompt, limit=WEB_SEARCH_SOURCE_LIMIT)
    except Exception:
        return None
    if not results:
        return None
    return _build_web_answer(prompt, results)


def _build_web_context(results: List[dict]) -> str:
    context_lines = []
    for idx, item in enumerate(results[:WEB_SEARCH_SOURCE_LIMIT], start=1):
        title = str(item.get('title', '')).strip()
        snippet = str(item.get('snippet', '')).strip()
        if title or snippet:
            context_lines.append(f'{idx}. {title} - {snippet}'.strip(' -'))
    return _truncate_by_words('\n'.join(context_lines), WEB_SEARCH_WORD_LIMIT)


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


def _apply_language_instruction(prompt_for_model: str, original_prompt: str) -> str:
    _ = original_prompt
    return (
        'Luôn trả lời bằng tiếng Việt có dấu, ngắn gọn và rõ ràng. '
        'Nếu chưa chắc, hãy trả lời phần biết được và hỏi lại ngắn gọn '
        'thay vì trả về câu từ chối cứng.\n\n'
        f'Yêu cầu người dùng:\n{prompt_for_model}'
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
            f"{'Người dùng' if item.sender == 'user' else 'Trợ lý'}: {item.text}" for item in recent
        )
        facts = [item.strip() for item in (memory_facts or []) if item and item.strip()]
        memory_block = ''
        if facts:
            memory_block = (
                'Thông tin đã biết về người dùng (ưu tiên tận dụng, không hỏi lại khi đã đủ thông tin):\n'
                + '\n'.join(f'- {item}' for item in facts[-10:])
                + '\n\n'
            )

        composed_prompt = (
            'Bạn là trợ lý AI tiếng Việt cho hệ thống AIPA. '
            'Luôn trả lời bằng tiếng Việt có dấu, đúng trọng tâm, rõ ràng, thân thiện, không lan man. '
            'Trả lời ngắn gọn, tối đa 4 câu và không dùng markdown rườm rà. '
            'Chỉ dùng ngôn ngữ khác khi người dùng yêu cầu rõ ràng.\n\n'
            f'{memory_block}'
            f'Hội thoại gần đây:\n{history_lines if history_lines else "(không có)"}\n\n'
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
                ),
            }
        ]
        facts = [item.strip() for item in (memory_facts or []) if item and item.strip()]
        if facts:
            messages.append(
                {
                    'role': 'system',
                    'content': (
                        'Thông tin đã biết về người dùng, hãy tái sử dụng để tránh hỏi lặp lại:\n'
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
            f"{'Người dùng' if item.sender == 'user' else 'Trợ lý'}: {item.text}"
            for item in history[-10:]
        )
        facts_block = '\n'.join(f'- {item}' for item in facts[-10:]) if facts else '(không có)'

        composed_prompt = (
            'Bạn là trợ lý AI tiếng Việt cho hệ thống AIPA. '
            'Luôn trả lời bằng tiếng Việt có dấu, chính xác, rõ ràng, đúng trọng tâm, tối đa 24 câu. '
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
                message = str(data['error'].get('message', '')).strip() or 'Gemini trả lời không xác định.'
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
                    'Trả lời tối đa 24 câu, không markdown rườm rà. '
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
                        'Thông tin đã biết về người dùng, hãy tái sử dụng để tránh hỏi lặp lại:\n'
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
            raise ValueError('Dữ liệu ảnh không hợp lệ (base64).') from exc

        frame_bytes = np.frombuffer(raw_bytes, dtype=np.uint8)
        frame = cv2.imdecode(frame_bytes, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError('Không giải mã được ảnh.')
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
_REQUIREMENTS_CACHE: Tuple[Optional[int], List[str]] = (None, [])
_REQUIREMENTS_CACHE_LOCK = threading.Lock()
APP_LAUNCHER_CACHE_TTL_SECONDS = max(10, int(os.getenv('AIPA_APP_LAUNCHER_CACHE_TTL', '300')))
_MOUSE_KEYBOARD_CONTROLLER = None


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


def _load_requirements_lines() -> List[str]:
    file_mtime: Optional[int] = None
    if REQUIREMENTS_FILE.exists():
        try:
            file_mtime = REQUIREMENTS_FILE.stat().st_mtime_ns
        except OSError:
            file_mtime = None

    with _REQUIREMENTS_CACHE_LOCK:
        cached_mtime, cached_items = _REQUIREMENTS_CACHE
        if cached_items and cached_mtime == file_mtime:
            return cached_items

    items: List[str] = []
    if REQUIREMENTS_FILE.exists():
        try:
            raw_lines = REQUIREMENTS_FILE.read_text(encoding='utf-8').splitlines()
        except Exception:
            raw_lines = []
        for line in raw_lines:
            clean = line.strip()
            if not clean or clean.startswith('#'):
                continue
            items.append(clean)

    with _REQUIREMENTS_CACHE_LOCK:
        _REQUIREMENTS_CACHE = (file_mtime, items)

    return items


def _answer_from_requirements(prompt: str) -> Optional[str]:
    clean = _normalize_match_ascii(prompt)
    if not clean:
        return None

    requirement_markers = (
        'requirements',
        'requirement',
        'phu thuoc',
        'dependencies',
        'thu vien',
        'cai dat',
        'yeu cau',
        'moi truong',
        'can cai',
        'can nhung gi',
        'pip',
    )
    if not any(marker in clean for marker in requirement_markers):
        return None

    items = _load_requirements_lines()
    if not items:
        return None

    return 'Các gói cần cài: ' + ', '.join(items)


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
    # Optional prefixes to make computer-control prompts explicit, without affecting existing triggers.
    # Examples: "máy tính: mở chrome", "pc - click a1", "lệnh: gõ chữ hello"
    pattern = r'^\s*(giong noi|voice|may tinh|máy tính|computer|pc|lenh|lệnh|command|control)\s*[:\-]?\s*'
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


def _ensure_desktop_write_target(path: Path):
    target = Path(path).resolve()
    try:
        target.relative_to(CONTROL_DESKTOP_ROOT)
    except ValueError as exc:
        raise PermissionError(
            f'Chỉ được thao tác file/thư mục trong Desktop: {CONTROL_DESKTOP_ROOT.as_posix()}'
        ) from exc

    blocked_system_parts = {
        'windows',
        'system32',
        'program files',
        'program files (x86)',
        'boot',
    }
    lowered_parts = {part.strip().lower() for part in target.parts}
    if lowered_parts.intersection(blocked_system_parts):
        raise PermissionError('Đường dẫn nhạy cảm hệ thống. Từ chối thao tác để bảo vệ máy.')


def _resolve_desktop_write_path(raw_path: str) -> Path:
    raw = (raw_path or '').strip()
    if not raw:
        raise ValueError('Thiếu đường dẫn trong tập lệnh.')

    expanded = os.path.expandvars(os.path.expanduser(raw))
    path_obj = Path(expanded)
    if not path_obj.is_absolute():
        path_obj = CONTROL_DESKTOP_ROOT / path_obj
    resolved = path_obj.resolve()
    _ensure_desktop_write_target(resolved)
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
    if path == CONTROL_DESKTOP_ROOT:
        raise PermissionError('Không được xóa thư mục Desktop root.')
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
        return 'Không hỗ trợ quét đồng hồ desktop trên hệ điều hành này.'

    try:
        user32 = ctypes.windll.user32
    except Exception as exc:
        return f'Không truy cập được WinAPI để quét desktop clock: {exc}'

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
        return 'Không tìm thấy taskbar để quét đồng hồ desktop.'

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
    return f'Không đọc được text đồng hồ từ desktop. Giờ hệ thống hiện tại: {now_local}.'


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


def _suggest_windows_app_names(app_name: str, limit: int = 6) -> List[str]:
    if os.name != 'nt':
        return []

    query = _normalize_match_ascii(app_name)
    tokens = [token for token in query.split() if token]
    if not tokens:
        return []

    scored: Dict[str, Tuple[int, str]] = {}

    def add_candidate(display_name: str, score: int):
        if score < 18:
            return
        cleaned_name = str(display_name or '').strip()
        if not cleaned_name:
            return
        key = _normalize_match_ascii(cleaned_name)
        if not key:
            return
        current = scored.get(key)
        if current is None or score > current[0]:
            scored[key] = (score, cleaned_name)

    roots = []
    program_data = os.getenv('ProgramData', '').strip()
    app_data = os.getenv('APPDATA', '').strip()
    if program_data:
        roots.append(Path(program_data) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs')
    if app_data:
        roots.append(Path(app_data) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs')

    for root in roots:
        if not root.exists():
            continue
        try:
            for shortcut_path in root.rglob('*.lnk'):
                score = _score_app_name_match(shortcut_path.stem, query, tokens)
                add_candidate(shortcut_path.stem, score)
        except Exception:
            continue

    alias_index = _load_windowsapps_alias_index()
    for alias_key in alias_index.keys():
        score = _score_app_name_match(alias_key, query, tokens)
        add_candidate(alias_key, score)

    running_processes = _list_running_windows_processes()
    for image_name, _pid in running_processes:
        process_name = Path(image_name).stem
        score = _score_app_name_match(process_name, query, tokens)
        add_candidate(process_name, score)

    if not scored:
        return []

    ranked = sorted(
        scored.values(),
        key=lambda item: (item[0], SequenceMatcher(None, _normalize_match_ascii(item[1]), query).ratio()),
        reverse=True,
    )
    return [name for _score, name in ranked[: max(1, limit)]]


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

    suggestions = _suggest_windows_app_names(target, limit=6)
    if suggestions:
        raise FileNotFoundError(
            'Không tìm thấy ứng dụng cần mở. Có thể bạn muốn mở: ' + ', '.join(suggestions)
        )
    raise FileNotFoundError('Không tìm thấy ứng dụng cần mở. Hãy kiểm tra lại tên app.')

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


def _get_mouse_keyboard_controller():
    global _MOUSE_KEYBOARD_CONTROLLER
    if _MOUSE_KEYBOARD_CONTROLLER is not None:
        return _MOUSE_KEYBOARD_CONTROLLER

    try:
        from controllers.mouse_keyboard_controller import MouseKeyboardController
    except Exception as exc:
        raise RuntimeError(f'Không tải được bộ điều khiển chuột/phím: {exc}') from exc

    _MOUSE_KEYBOARD_CONTROLLER = MouseKeyboardController()
    return _MOUSE_KEYBOARD_CONTROLLER


def _get_screen_size_for_control() -> Tuple[int, int]:
    try:
        user32 = ctypes.windll.user32
        width = int(user32.GetSystemMetrics(0))
        height = int(user32.GetSystemMetrics(1))
        if width > 0 and height > 0:
            return width, height
    except Exception:
        pass
    return 1920, 1080


def _parse_mouse_target(raw_target: str) -> Tuple[int, int]:
    target = str(raw_target or '').strip()
    if not target:
        raise ValueError('Toa do chuot dang trong.')

    grid_target = _normalize_match_ascii(target)
    if re.match(r'^[a-z][0-9]+$', grid_target):
        try:
            from utils.coordinate_resolver import CoordinateResolver
        except Exception as exc:
            raise RuntimeError(f'Không tải được bộ giải tọa độ lưới: {exc}') from exc

        screen_width, screen_height = _get_screen_size_for_control()
        resolver = CoordinateResolver(
            rows=CONTROL_GRID_ROWS,
            cols=CONTROL_GRID_COLS,
            screen_width=screen_width,
            screen_height=screen_height,
        )
        return resolver.resolve(grid_target)

    point_match = re.match(r'^\s*(-?\d+)\s*(?:,|\s)\s*(-?\d+)\s*$', target)
    if not point_match:
        raise ValueError('Tọa độ không hợp lệ. Dùng dạng "x,y", "x y" hoặc tọa độ lưới như "c3".')

    x = int(point_match.group(1))
    y = int(point_match.group(2))
    if x < 0 or y < 0:
        raise ValueError('Toa do x/y phai >= 0.')
    return x, y


def _split_drag_targets(raw_text: str) -> Tuple[str, str]:
    text = str(raw_text or '').strip()
    if not text:
        raise ValueError('Thieu toa do cho lenh keo chuot.')

    grid_pair = re.match(r'^\s*([a-z][0-9]+)\s*(?:->|to|den)\s*([a-z][0-9]+)\s*$', _normalize_match_ascii(text))
    if grid_pair:
        return grid_pair.group(1), grid_pair.group(2)

    point_pair = re.match(
        r'^\s*(-?\d+\s*(?:,|\s)\s*-?\d+)\s*(?:->|to|den)\s*(-?\d+\s*(?:,|\s)\s*-?\d+)\s*$',
        text,
        flags=re.IGNORECASE,
    )
    if point_pair:
        return point_pair.group(1), point_pair.group(2)

    four_numbers_csv = re.match(r'^\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*$', text)
    if four_numbers_csv:
        return (
            f'{four_numbers_csv.group(1)},{four_numbers_csv.group(2)}',
            f'{four_numbers_csv.group(3)},{four_numbers_csv.group(4)}',
        )

    four_numbers_space = re.match(r'^\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*$', text)
    if four_numbers_space:
        return (
            f'{four_numbers_space.group(1)} {four_numbers_space.group(2)}',
            f'{four_numbers_space.group(3)} {four_numbers_space.group(4)}',
        )

    parts = [part for part in text.split() if part]
    if len(parts) == 2:
        return parts[0], parts[1]

    raise ValueError('Lenh keo chuot can 2 diem. Vi du: "a1 b3" hoac "100,200 -> 300,400".')


def _parse_hotkey_tokens(raw_keys: str) -> List[str]:
    normalized = _normalize_match_ascii(raw_keys)
    if not normalized:
        raise ValueError('Lenh phim tat dang trong.')
    return [token for token in re.split(r'[\s+,]+', normalized) if token]


def _split_rest_path_and_text(raw_text: str) -> Tuple[str, str]:
    """
    Parse a user-friendly "<path> <text...>" payload from {REST}.

    Supports:
    - "file.txt noi dung ..."
    - "file.txt|noi dung ..."
    - "file.txt: noi dung ..."
    """
    text = str(raw_text or '').strip()
    if not text:
        raise ValueError('Thiếu đường dẫn và nội dung.')

    for delimiter in ('|', ':'):
        if delimiter in text:
            left, right = text.split(delimiter, 1)
            path_part = left.strip()
            body_part = right.strip()
            if not path_part:
                raise ValueError('Thiếu đường dẫn trước dấu phân cách.')
            return path_part, body_part

    parts = text.split(None, 1)
    path_part = parts[0].strip()
    body_part = parts[1].strip() if len(parts) > 1 else ''
    if not path_part:
        raise ValueError('Thiếu đường dẫn.')
    return path_part, body_part


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

    if command in {'CLICK', 'LEFT_CLICK', 'MOUSE_CLICK', 'MOUSE_LEFT_CLICK'}:
        if len(parts) < 2:
            raise ValueError(f'Hanh dong {command} can toa do chuot.')
        target_raw = _render_control_value('|'.join(parts[1:]), prompt, prompt_tail)
        x, y = _parse_mouse_target(target_raw)
        controller = _get_mouse_keyboard_controller()
        controller.mouse.left_click((x, y))
        return f'Da click chuot trai tai ({x}, {y}).'

    if command in {'RIGHT_CLICK', 'MOUSE_RIGHT_CLICK'}:
        if len(parts) < 2:
            raise ValueError(f'Hanh dong {command} can toa do chuot.')
        target_raw = _render_control_value('|'.join(parts[1:]), prompt, prompt_tail)
        x, y = _parse_mouse_target(target_raw)
        controller = _get_mouse_keyboard_controller()
        controller.mouse.right_click((x, y))
        return f'Da click chuot phai tai ({x}, {y}).'

    if command in {'DRAG_MOUSE', 'MOUSE_DRAG', 'DRAG'}:
        if len(parts) >= 3:
            start_raw = _render_control_value(parts[1], prompt, prompt_tail)
            end_raw = _render_control_value('|'.join(parts[2:]), prompt, prompt_tail)
        elif len(parts) == 2:
            drag_text = _render_control_value(parts[1], prompt, prompt_tail)
            start_raw, end_raw = _split_drag_targets(drag_text)
        else:
            raise ValueError(f'Hanh dong {command} can diem bat dau va diem ket thuc.')

        start = _parse_mouse_target(start_raw)
        end = _parse_mouse_target(end_raw)
        controller = _get_mouse_keyboard_controller()
        controller.mouse.drag(start, end)
        return f'Da keo chuot tu {start} den {end}.'

    if command in {'SCROLL', 'MOUSE_SCROLL'}:
        if len(parts) < 2:
            raise ValueError(f'Hanh dong {command} can huong cuon.')
        direction = _normalize_match_ascii(_render_control_value(parts[1], prompt, prompt_tail))
        amount = 2
        if len(parts) >= 3:
            amount_text = _render_control_value(parts[2], prompt, prompt_tail).strip()
            if amount_text:
                amount = abs(int(amount_text))
                if amount == 0:
                    amount = 1
        controller = _get_mouse_keyboard_controller()
        if direction in {'up', 'len'}:
            controller.mouse.scroll_up(amount)
            return f'Da cuon chuot len {amount} buoc.'
        if direction in {'down', 'xuong'}:
            controller.mouse.scroll_down(amount)
            return f'Da cuon chuot xuong {amount} buoc.'
        raise ValueError('Hướng cuộn không hợp lệ. Dùng "up/len" hoặc "down/xuong".')

    if command in {'TYPE_TEXT', 'TYPE', 'KEYBOARD_TYPE', 'TEXT'}:
        if len(parts) < 2:
            raise ValueError(f'Hành động {command} cần nội dung cần gõ.')
        text_to_type = _render_control_value('|'.join(parts[1:]), prompt, prompt_tail)
        if not text_to_type.strip():
            raise ValueError('Nội dung gõ đang trống.')
        controller = _get_mouse_keyboard_controller()
        controller.keyboard.type_text(text_to_type)
        return f'Da go {len(text_to_type)} ky tu.'

    if command in {'PRESS_KEYS', 'PRESS', 'HOTKEY', 'KEY_COMBO', 'KEYBOARD_PRESS'}:
        if len(parts) < 2:
            raise ValueError(f'Hanh dong {command} can to hop phim.')
        key_text = _render_control_value('|'.join(parts[1:]), prompt, prompt_tail)
        keys = _parse_hotkey_tokens(key_text)
        controller = _get_mouse_keyboard_controller()
        controller.keyboard.press_combination(keys)
        return f'Da nhan to hop phim: {" + ".join(keys)}.'

    if command in {'WAIT', 'SLEEP', 'DELAY'}:
        if len(parts) < 2:
            raise ValueError(f'Hành động {command} cần số giây cần chờ.')
        seconds_text = _render_control_value('|'.join(parts[1:]), prompt, prompt_tail).strip()
        try:
            seconds = float(seconds_text)
        except ValueError as exc:
            raise ValueError('Số giây chờ không hợp lệ.') from exc
        if seconds < 0:
            raise ValueError('Số giây chờ phải >= 0.')
        if seconds > 30:
            raise ValueError('Giới hạn WAIT tối đa 30 giây để tránh treo tác vụ.')
        time.sleep(seconds)
        return f'Đã chờ {seconds:g} giây.'

    if command in {'OPEN_URL', 'OPENURL', 'BROWSE_URL', 'OPEN_WEB', 'OPEN_WEBSITE'}:
        if len(parts) < 2:
            raise ValueError(f'Hành động {command} cần URL.')
        raw_url = _render_control_value('|'.join(parts[1:]), prompt, prompt_tail).strip()
        if not raw_url:
            raise ValueError('URL đang trống.')
        url = raw_url
        if not re.match(r'^(https?://)', url, flags=re.IGNORECASE):
            url = 'https://' + url
        if not re.match(r'^https?://', url, flags=re.IGNORECASE):
            raise ValueError('Chỉ hỗ trợ URL dạng http/https.')
        if os.name == 'nt':
            subprocess.run(['cmd', '/c', 'start', '', url], check=False)
            return f'Đã mở URL: {url}'
        raise OSError('Hành động OPEN_URL hiện chỉ hỗ trợ trên Windows.')

    # Desktop scope (safe default): open/list operate inside Desktop root.
    if command in {'OPEN_FILE', 'READ_FILE', 'OPEN', 'READ'}:
        raw_path = _render_control_value(parts[1], prompt, prompt_tail) if len(parts) >= 2 else ''
        raw_path = str(raw_path or '').strip()
        if not raw_path:
            return _list_dir_preview(CONTROL_DESKTOP_ROOT)
        file_path = _resolve_desktop_write_path(raw_path)
        if not file_path.exists():
            raise FileNotFoundError('Không tìm thấy tệp hoặc thư mục trong Desktop.')
        if file_path.is_dir():
            return _list_dir_preview(file_path)
        return _read_file_preview(file_path)

    if command in {'LIST_DIR', 'LS'}:
        raw_path = _render_control_value(parts[1], prompt, prompt_tail) if len(parts) >= 2 else ''
        raw_path = str(raw_path or '').strip()
        if not raw_path:
            return _list_dir_preview(CONTROL_DESKTOP_ROOT)
        dir_path = _resolve_desktop_write_path(raw_path)
        if not dir_path.exists():
            raise FileNotFoundError('Không tìm thấy thư mục trong Desktop.')
        if not dir_path.is_dir():
            raise NotADirectoryError('Mục đã chọn không phải thư mục.')
        return _list_dir_preview(dir_path)

    # Control/project scope: explicitly open/list inside COMPUTER_CONTROL_ROOT.
    if command in {
        'OPEN_CONTROL_FILE',
        'OPENCONTROLFILE',
        'READ_CONTROL_FILE',
        'READCONTROLFILE',
        'OPEN_PROJECT_FILE',
        'OPENPROJECTFILE',
        'READ_PROJECT_FILE',
        'READPROJECTFILE',
    }:
        if len(parts) < 2:
            raise ValueError(f'Hành động {command} cần 1 tham số đường dẫn.')
        file_path = _resolve_control_path(_render_control_value(parts[1], prompt, prompt_tail))
        if not file_path.exists():
            raise FileNotFoundError('Không tìm thấy tệp hoặc thư mục trong vùng control root.')
        if file_path.is_dir():
            return _list_dir_preview(file_path)
        return _read_file_preview(file_path)

    if command in {
        'LIST_CONTROL_DIR',
        'LISTCONTROLDIR',
        'LS_CONTROL',
        'LSCONTROL',
        'LIST_PROJECT_DIR',
        'LISTPROJECTDIR',
        'LS_PROJECT',
        'LSPROJECT',
    }:
        raw_path = _render_control_value(parts[1], prompt, prompt_tail) if len(parts) >= 2 else ''
        raw_path = str(raw_path or '').strip()
        if not raw_path:
            dir_path = COMPUTER_CONTROL_ROOT
        else:
            dir_path = _resolve_control_path(raw_path)
        if not dir_path.exists():
            raise FileNotFoundError('Không tìm thấy thư mục trong vùng control root.')
        if not dir_path.is_dir():
            raise NotADirectoryError('Mục đã chọn không phải thư mục.')
        return _list_dir_preview(dir_path)

    if command in {'WRITE_FILE_REST', 'WRITEFILEREST', 'WRITE_REST', 'WRITEREST'}:
        if len(parts) < 2:
            raise ValueError(f'Hành động {command} cần "<path> <nội dung...>" hoặc "<path>|<nội dung...>".')
        payload = _render_control_value('|'.join(parts[1:]), prompt, prompt_tail)
        path_part, body_part = _split_rest_path_and_text(payload)
        if not body_part:
            raise ValueError('Thiếu nội dung cần ghi. Ví dụ: "ghi file note.txt: hello".')
        file_path = _resolve_desktop_write_path(path_part)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(body_part, encoding='utf-8')
        return f'Đã ghi tệp ({len(body_part)} ký tự).'

    if command in {'APPEND_FILE_REST', 'APPENDFILEREST', 'APPEND_REST', 'APPENDREST'}:
        if len(parts) < 2:
            raise ValueError(f'Hành động {command} cần "<path> <nội dung...>" hoặc "<path>|<nội dung...>".')
        payload = _render_control_value('|'.join(parts[1:]), prompt, prompt_tail)
        path_part, body_part = _split_rest_path_and_text(payload)
        if not body_part:
            raise ValueError('Thiếu nội dung cần thêm. Ví dụ: "thêm vào file note.txt: dong 1".')
        file_path = _resolve_desktop_write_path(path_part)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open('a', encoding='utf-8') as handler:
            handler.write(body_part)
        return f'Đã thêm vào tệp ({len(body_part)} ký tự).'

    if command in {'WRITE_FILE', 'WRITE'}:
        if len(parts) < 3:
            raise ValueError(f'Hành động {command} cần đường dẫn và nội dung.')
        file_path = _resolve_desktop_write_path(_render_control_value(parts[1], prompt, prompt_tail))
        content_raw = '|'.join(parts[2:])
        content = _render_control_value(content_raw, prompt, prompt_tail)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
        return f'Đã ghi tệp ({len(content)} ký tự).'

    if command in {'APPEND_FILE', 'APPEND'}:
        if len(parts) < 3:
            raise ValueError(f'Hành động {command} cần đường dẫn và nội dung.')
        file_path = _resolve_desktop_write_path(_render_control_value(parts[1], prompt, prompt_tail))
        content_raw = '|'.join(parts[2:])
        content = _render_control_value(content_raw, prompt, prompt_tail)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open('a', encoding='utf-8') as handler:
            handler.write(content)
        return f'Đã thêm vào tệp ({len(content)} ký tự).'

    if command in {'CREATE_FILE', 'TOUCH_FILE'}:
        if len(parts) < 2:
            raise ValueError(f'Hành động {command} cần 1 tham số đường dẫn.')
        file_path = _resolve_desktop_write_path(_render_control_value(parts[1], prompt, prompt_tail))
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
        dir_path = _resolve_desktop_write_path(_render_control_value(parts[1], prompt, prompt_tail))
        dir_path.mkdir(parents=True, exist_ok=True)
        return 'Đã tạo thư mục.'

    if command in {'DELETE_FILE', 'REMOVE_FILE'}:
        if len(parts) < 2:
            raise ValueError(f'Hành động {command} cần 1 tham số đường dẫn.')
        file_path = _resolve_desktop_write_path(_render_control_value(parts[1], prompt, prompt_tail))
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
        dir_path = _resolve_desktop_write_path(_render_control_value(parts[1], prompt, prompt_tail))
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
        path = _resolve_desktop_write_path(_render_control_value(parts[1], prompt, prompt_tail))
        _ensure_deletion_allowed(path)
        if not path.exists():
            return 'Không tìm thấy mục để xóa.'
        if path.is_dir():
            shutil.rmtree(path)
            return 'Đã xóa thư mục.'
        path.unlink()
        return 'Đã xóa tệp.'

    raise ValueError(f'Hành động không hỗ trợ: {command}')


def _is_computer_control_help_prompt(prompt: str) -> bool:
    clean = _normalize_match_ascii(prompt)
    if not clean:
        return False

    help_markers = (
        'huong dan dieu khien',
        'help dieu khien',
        'danh sach lenh',
        'lenh dieu khien',
        'lenh may tinh',
        'computer control help',
        'control help',
        'help control',
        'cach dieu khien',
        'cach dung lenh',
    )
    return any(marker in clean for marker in help_markers)


def _render_computer_control_help_text() -> str:
    rules = _load_computer_control_rules()
    triggers = [str(rule.get('trigger_display', '')).strip() for rule in rules]
    triggers = [t for t in triggers if t]

    quick_examples = [
        'máy tính: mở chrome',
        'máy tính: đóng chrome',
        'máy tính: click a1',
        'máy tính: click 1200,700',
        'máy tính: kéo chuột a1 -> c3',
        'máy tính: cuộn xuống',
        'máy tính: gõ chữ xin chào',
        'máy tính: nhấn phím ctrl+l',
        'máy tính: tạo file ghi_chu.txt',
        'máy tính: ghi đè file ghi_chu.txt nội dung hôm nay {NOW}',
        'máy tính: mở file ghi_chu.txt',
        'máy tính: liệt kê desktop',
        'máy tính: mở web openai.com',
    ]

    doc_hint = ''
    if COMPUTER_CONTROL_DOC_FILE.exists():
        doc_hint = f'Tài liệu đầy đủ: {COMPUTER_CONTROL_DOC_FILE.as_posix()}'

    lines = []
    lines.append('Hướng dẫn điều khiển máy tính (prompt):')
    lines.append('')
    lines.append('Ví dụ nhanh (có thể thêm tiền tố "máy tính:" / "pc:" / "lệnh:" để rõ nghĩa):')
    lines.extend([f'- {item}' for item in quick_examples])
    lines.append('')
    if triggers:
        lines.append(f'Trigger đã cấu hình ({min(len(triggers), 40)}/{len(triggers)}):')
        for item in triggers[:40]:
            lines.append(f'- {item}')
        if len(triggers) > 40:
            lines.append(f'... và {len(triggers) - 40} trigger khác.')
        lines.append('')
    lines.append(f'Tệp train: {COMPUTER_CONTROL_TRAIN_FILE.as_posix()}')
    if doc_hint:
        lines.append(doc_hint)
    lines.append('API: GET /api/computer-control/help, GET /api/computer-control/rules')
    return '\n'.join(lines).strip()


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
                    action.upper().startswith(
                        (
                            'OPEN_APP|',
                            'CLOSE_APP|',
                            'KILL_APP|',
                            'STOP_APP|',
                            'TERMINATE_APP|',
                            'CLICK|',
                            'RIGHT_CLICK|',
                            'DRAG_MOUSE|',
                            'TYPE_TEXT|',
                            'PRESS_KEYS|',
                            'OPEN_URL|',
                            'WAIT|',
                            'OPEN_FILE|',
                            'LIST_DIR|',
                            'WRITE_FILE_REST|',
                            'APPEND_FILE_REST|',
                            'WRITE_FILE|',
                            'APPEND_FILE|',
                            'CREATE_FILE|',
                            'CREATE_DIR|',
                            'DELETE_FILE|',
                            'DELETE_DIR|',
                            'DELETE_PATH|',
                        )
                    )
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
        except Exception as exc:
            error_text = str(exc).strip() or 'Không thực hiện được lệnh này.'
            action_logs.append(f'{idx}. {error_text}')
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

    if 'trung quoc' in clean:
        if any(marker in clean for marker in ('khai sinh', 'tu bao gio', 'thanh lap', 'ra doi', 'lap nuoc')):
            return (
                'Cộng hòa Nhân dân Trung Hoa được thành lập ngày 01/10/1949. '
                'Nếu bạn hỏi về lịch sử Trung Quốc cổ đại hoặc triều đại, vui lòng nêu mốc cụ thể.'
            )
        if 'o dau' in clean or 'nam o dau' in clean:
            return (
                'Trung Quốc nằm ở Đông Á, giáp 14 quốc gia và có bờ biển dài '
                'giáp Hoàng Hải, Hoa Đông và Biển Đông.'
            )

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
    if 'khong the thuc hien yeu cau' in normalized_ascii:
        return True
    if (
        'khong' in normalized_ascii
        and 'yeu cu' in normalized_ascii
        and 'vui' in normalized_ascii
        and ('thu' in normalized_ascii or 'th li' in normalized_ascii)
    ):
        return True
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

    cleaned_chars = []
    for ch in text:
        if ch in {'\n', '\r', '\t', ' '}:
            cleaned_chars.append(ch)
            continue
        category = unicodedata.category(ch)
        if category.startswith('C'):
            # Drop control characters but keep visible text from any script.
            continue
        cleaned_chars.append(ch)

    text_out = ''.join(cleaned_chars)
    text_out = re.sub(r'[ \t]{2,}', ' ', text_out)
    text_out = re.sub(r'\n{3,}', '\n\n', text_out)
    return text_out.strip()


_MOJIBAKE_RE = re.compile(
    r'(?:Ã.|Ä.|Æ.|á»|áº|â€|�|\ufffd)',
    flags=re.UNICODE,
)


def _looks_like_mojibake(text: str) -> bool:
    sample = str(text or '')
    if not sample:
        return False
    return bool(_MOJIBAKE_RE.search(sample))


def _repair_mojibake_text(text: str) -> str:
    raw = str(text or '')
    if not raw:
        return ''
    if not _looks_like_mojibake(raw):
        return raw

    # Typical cause: UTF-8 bytes mis-decoded as a legacy single-byte codec.
    candidates = [raw]
    for legacy_codec in ('cp1252', 'latin-1', 'cp1258'):
        try:
            repaired = raw.encode(legacy_codec, errors='strict').decode('utf-8', errors='strict')
        except Exception:
            continue
        if repaired and repaired != raw:
            candidates.append(repaired)

    def score(value: str) -> tuple:
        # Lower mojibake count is better; higher Vietnamese mark count is better.
        bad = len(_MOJIBAKE_RE.findall(value))
        nfd = unicodedata.normalize('NFD', value)
        marks = sum(1 for ch in nfd if unicodedata.category(ch) == 'Mn') + value.count('đ') + value.count('Đ')
        return (bad, -marks, -len(value))

    return sorted(candidates, key=score)[0]


def _postprocess_answer(answer: str, max_len: int = 1400) -> str:
    clean = (answer or '').strip()
    if not clean:
        return ''

    clean = clean.replace('**', '').replace('`', '')
    clean = unicodedata.normalize('NFC', clean)
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


def _has_vietnamese_diacritics(text: str) -> bool:
    if not text:
        return False
    if 'đ' in text or 'Đ' in text:
        return True
    normalized = unicodedata.normalize('NFD', text)
    return any(unicodedata.category(ch) == 'Mn' for ch in normalized)


def _needs_vietnamese_diacritics(text: str) -> bool:
    if not text:
        return False
    if not any(ch.isalpha() for ch in text):
        return False
    return not _has_vietnamese_diacritics(text)


def _rewrite_with_diacritics(answer: str, generate_fn, max_len: int = 1400) -> str:
    prompt = (
        'Hãy viết lại đoạn sau bằng tiếng Việt có dấu đầy đủ. '
        'Giữ nguyên nội dung, không thêm bớt, không đổi ý. '
        'Nếu có tên riêng hoặc thuật ngữ tiếng Anh, giữ nguyên.\n\n'
        f'Đoạn:\n{answer}'
    )
    try:
        raw = generate_fn(prompt)
    except Exception:
        return ''
    rewritten = _finalize_answer_for_response(raw, max_len=max_len)
    if rewritten and _has_vietnamese_diacritics(rewritten):
        return rewritten
    return ''


def _finalize_answer_for_response(answer: str, max_len: int = 1400) -> str:
    clean = _postprocess_answer(answer, max_len=max_len)
    if not clean:
        return ''

    return clean


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
            'trong giai đoạn 1927-1949 (gián đoạn thời kỳ kháng Nhật).',
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
        'computer_control_build': COMPUTER_CONTROL_BUILD_TAG,
        'service_file': Path(__file__).resolve().as_posix(),
        'service_base_dir': BASE_DIR.as_posix(),
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
        'computer_control_train_mtime_ns': (
            COMPUTER_CONTROL_TRAIN_FILE.stat().st_mtime_ns if COMPUTER_CONTROL_TRAIN_FILE.exists() else None
        ),
        'computer_control_root': COMPUTER_CONTROL_ROOT.as_posix(),
        'computer_control_allow_any_path': COMPUTER_CONTROL_ALLOW_ANY_PATH,
        'computer_control_allow_delete': COMPUTER_CONTROL_ALLOW_DELETE,
        'knowledge_size': knowledge_store.knowledge_size(),
        'memory_sessions': conversation_store.session_count(),
    }


@app.post('/api/train')
def train_qa(request: TrainRequest):
    knowledge_store.add_pair(
        _repair_mojibake_text(request.question),
        _repair_mojibake_text(request.answer),
    )
    return {
        'message': 'Đã cập nhật dữ liệu train thành công.',
        'knowledge_size': knowledge_store.knowledge_size(),
    }


@app.get('/api/computer-control/rules')
def computer_control_rules():
    rules = _load_computer_control_rules() if COMPUTER_CONTROL_ENABLED else []
    return {
        'enabled': COMPUTER_CONTROL_ENABLED,
        'train_file': COMPUTER_CONTROL_TRAIN_FILE.as_posix(),
        'doc_file': COMPUTER_CONTROL_DOC_FILE.as_posix(),
        'desktop_root': CONTROL_DESKTOP_ROOT.as_posix(),
        'control_root': COMPUTER_CONTROL_ROOT.as_posix(),
        'allow_any_path': COMPUTER_CONTROL_ALLOW_ANY_PATH,
        'allow_delete': COMPUTER_CONTROL_ALLOW_DELETE,
        'rules': rules,
    }


@app.get('/api/computer-control/help')
def computer_control_help():
    return {
        'enabled': COMPUTER_CONTROL_ENABLED,
        'help': _render_computer_control_help_text(),
        'train_file': COMPUTER_CONTROL_TRAIN_FILE.as_posix(),
        'doc_file': COMPUTER_CONTROL_DOC_FILE.as_posix(),
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

    learned_answer = knowledge_store.find_answer(request.prompt)
    if learned_answer:
        learned_answer = _finalize_answer_for_response(learned_answer)
        conversation_store.append_exchange(session_id, request.prompt, learned_answer)
        return ChatResponse(answer=learned_answer, source='knowledge', model='knowledge_store')

    requirements_answer = _answer_from_requirements(request.prompt)
    if requirements_answer:
        requirements_answer = _finalize_answer_for_response(requirements_answer, max_len=1200)
        if requirements_answer:
            conversation_store.append_exchange(session_id, request.prompt, requirements_answer)
            return ChatResponse(answer=requirements_answer, source='knowledge', model='requirements_chat')

    if _is_computer_control_help_prompt(request.prompt):
        help_text = _render_computer_control_help_text()
        help_text = _finalize_answer_for_response(help_text, max_len=2600)
        conversation_store.append_exchange(session_id, request.prompt, help_text)
        return ChatResponse(answer=help_text, source='fallback', model='computer_control_help')

    computer_control_answer = _try_execute_computer_control(request.prompt)
    if computer_control_answer:
        computer_control_answer = _finalize_answer_for_response(computer_control_answer, max_len=1800)
        conversation_store.append_exchange(session_id, request.prompt, computer_control_answer)
        return ChatResponse(answer=computer_control_answer, source='fallback', model='computer_control_train')

    word_chain_answer = _handle_word_chain_prompt(request.prompt, session_id, conversation_store)
    if word_chain_answer:
        word_chain_answer = _finalize_answer_for_response(word_chain_answer)
        conversation_store.append_exchange(session_id, request.prompt, word_chain_answer)
        return ChatResponse(answer=word_chain_answer, source='fallback', model='word_chain')

    rule_answer = _rule_based_answer(request.prompt)
    if rule_answer:
        rule_answer = _finalize_answer_for_response(rule_answer)
        conversation_store.append_exchange(session_id, request.prompt, rule_answer)
        return ChatResponse(answer=rule_answer, source='fallback', model='rule_based')

    contextual_answer = _contextual_rule_answer(request.prompt, merged_history)
    if contextual_answer:
        contextual_answer = _finalize_answer_for_response(contextual_answer)
        conversation_store.append_exchange(session_id, request.prompt, contextual_answer)
        return ChatResponse(answer=contextual_answer, source='fallback', model='contextual_rule')

    prompt_for_model = _apply_language_instruction(prompt_for_model, request.prompt)

    generated_answer = ''
    web_answer = None
    web_allowed = (
        WEB_SEARCH_ENABLED
        and WEB_SEARCH_MODE != 'off'
        and web_search_service.active
        and web_search_service.google_ready
    )
    ollama_attempted = False

    if ollama_chat_model.enabled:
        ollama_attempted = True
        raw_answer = ''
        try:
            raw_answer = ollama_chat_model.generate(prompt_for_model, merged_history, memory_facts)
        except Exception as exc:
            raw_answer = ''
        generated_answer = _postprocess_answer(raw_answer)
        generated_answer = _sanitize_historical_answer(request.prompt, merged_history, generated_answer)
        generated_answer = _finalize_answer_for_response(generated_answer)

        if generated_answer:
            if _needs_vietnamese_diacritics(generated_answer):
                rewritten = _rewrite_with_diacritics(
                    generated_answer,
                    lambda p: ollama_chat_model.generate(p, [], []),
                    max_len=1800,
                )
                if rewritten:
                    generated_answer = rewritten
                else:
                    generated_answer = 'Mình chưa thể tạo câu trả lời có dấu đầy đủ. Bạn thử lại giúp mình nhé.'
            conversation_store.append_exchange(session_id, request.prompt, generated_answer)
            return ChatResponse(answer=generated_answer, source='model', model=OLLAMA_MODEL_NAME)

    # If local LLM fails (common: not enough RAM), proactively use web search when available.
    if web_allowed and (should_lookup_web or (ollama_attempted and not generated_answer)):
        web_answer = _search_web_answer(request.prompt)
        if web_answer:
            answer = _finalize_answer_for_response(web_answer, max_len=1800)
            conversation_store.append_exchange(session_id, request.prompt, answer)
            return ChatResponse(answer=answer, source='web', model='web_search')

    if should_lookup_web and not web_allowed:
        web_notice = 'Hiện tại mình chưa thể tra cứu web. Bạn thử lại sau ít phút.'

    if HF_FALLBACK_ENABLED:
        raw_answer = ''
        try:
            raw_answer = text_model.generate(prompt_for_model, merged_history, memory_facts).strip()
        except Exception as exc:
            raw_answer = ''
        generated_answer = _postprocess_answer(raw_answer)
        generated_answer = _sanitize_historical_answer(request.prompt, merged_history, generated_answer)
        generated_answer = _finalize_answer_for_response(generated_answer)

        if generated_answer:
            if _needs_vietnamese_diacritics(generated_answer):
                rewritten = _rewrite_with_diacritics(
                    generated_answer,
                    lambda p: text_model.generate(p, [], []),
                    max_len=1800,
                )
                if rewritten:
                    generated_answer = rewritten
                else:
                    generated_answer = 'Mình chưa thể tạo câu trả lời có dấu đầy đủ. Bạn thử lại giúp mình nhé.'
            conversation_store.append_exchange(session_id, request.prompt, generated_answer)
            return ChatResponse(answer=generated_answer, source='model', model=MODEL_NAME)

    # Last resort: still try web search if models failed and web is available.
    if web_allowed and not web_answer:
        web_answer = _search_web_answer(request.prompt)
        if web_answer:
            answer = _finalize_answer_for_response(web_answer, max_len=1800)
            conversation_store.append_exchange(session_id, request.prompt, answer)
            return ChatResponse(answer=answer, source='web', model='web_search')

    if should_lookup_web and web_notice:
        fallback_answer = web_notice
    else:
        fallback_answer = (
            'Mình đã nhận câu hỏi nhưng hệ thống AI đang bận khởi động hoặc tạm thời quá tải. '
            'Bạn thử lại sau ít phút, hoặc đặt câu hỏi cụ thể hơn để mình trả lời tốt hơn.'
        )
    fallback_answer = _finalize_answer_for_response(fallback_answer, max_len=1800)
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
            detail='Không thể khởi tạo bộ mã hóa khuôn mặt.',
        ) from exc

    if not embedding:
        raise HTTPException(status_code=422, detail='Không tìm thấy khuôn mặt trong ảnh.')

    return FaceExtractResponse(
        status='ok',
        embedding=embedding,
        dimension=len(embedding),
    )


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('chat_server:app', host=HOST, port=PORT, reload=False)
