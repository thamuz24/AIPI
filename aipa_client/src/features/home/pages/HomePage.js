import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Settings, Lock, LogOut, Trash2, Send, Zap, Mic, Volume2, Shield, MessageSquarePlus, BookOpen, Grid3X3 } from 'lucide-react';
import styles from './HomePage.module.css';
import { useAuth } from '../../auth/context';
import { ANIME_MODEL_IMAGE_PATH } from '../model/animeModelConfig';
import { chatWithAssistantApi, trainAssistantApi, saveComputerControlRuleApi, fetchComputerControlRulesApi, showComputerControlOverlayApi, hideComputerControlOverlayApi } from '../../../shared/api';
import { appendPromptHistory, getUserSettings, patchUserSettings } from '../../../shared/services';

const EXPRESSIONS = [
  { key: 'happy', eyes: '^ ^', mouth: ':)', mood: 'D\u1ec5 th\u01b0\u01a1ng' },
  { key: 'smile', eyes: 'o o', mouth: ':D', mood: 'Th\u00e2n thi\u1ec7n' },
  { key: 'wink', eyes: '^ -', mouth: ';)', mood: 'Tinh ngh\u1ecbch' },
  { key: 'surprised', eyes: 'o o', mouth: ':o', mood: 'Ng\u1ea1c nhi\u00ean' },
];

const SESSION_KEY_PREFIX = 'aipa_chat_session_v1';
const FEMALE_VOICE_PROFILE = {
  rate: 1.02,
  pitch: 1.24,
};
const FEMALE_VOICE_HINTS = ['hoai my', 'hoaimy', 'female', 'woman', 'girl', 'zira', 'hazel', 'susan'];
const MALE_VOICE_HINTS = ['male', 'man', 'boy', 'nam', 'hung', 'minh', 'david', 'mark'];
const VBEE_TTS_URL = String(process.env.REACT_APP_VBEE_TTS_URL || '').trim();
const VBEE_TTS_TOKEN = String(process.env.REACT_APP_VBEE_TTS_TOKEN || '').trim();
const VBEE_TTS_APP_ID = String(process.env.REACT_APP_VBEE_TTS_APP_ID || '').trim();
const VBEE_VOICE_CODE = String(process.env.REACT_APP_VBEE_VOICE_CODE || 'hn_female_ngochuyen_full_48k-fhg').trim();
const SHOULD_USE_VBEE_TTS = Boolean(VBEE_TTS_URL && (VBEE_TTS_TOKEN || VBEE_TTS_APP_ID));
const START_VOICE_STANDBY_COMMANDS = [
  'khoi dong nhap giong noi',
  'bat dau nhap giong noi',
  'khoi dong giong noi',
  'bat giong noi',
];
const STOP_VOICE_STANDBY_COMMANDS = [
  'ket thuc nhap giong noi',
  'ket thuc giong noi',
  'dung nhap giong noi',
  'tat giong noi',
  'dung giong noi',
];
const STOP_VOICE_RESPONSE_COMMANDS = [
  'tat giong noi phan hoi',
  'tat giong doc',
  'tat doc',
  'im lang',
];
const START_VOICE_RESPONSE_COMMANDS = [
  'bat giong noi phan hoi',
  'bat giong doc',
  'bat doc',
  'doc phan hoi',
];
const getExpressionByKey = (key) => EXPRESSIONS.find((item) => item.key === key) || EXPRESSIONS[0];
const getWelcomeText = (username) => `Ch\u00e0o m\u1eebng tr\u1edf l\u1ea1i ${username}! T\u00f4i l\u00e0 tr\u1ee3 l\u00fd, b\u1ea1n c\u1ea7n h\u1ed7 tr\u1ee3 g\u00ec h\u00f4m nay?`;
const QUICK_TIPS = [
  'Nh\u1eadp 1 l\u1ec7nh trong m\u1ed7i tin nh\u1eafn, kh\u00f4ng g\u1ed9p nhi\u1ec1u t\u00e1c v\u1ee5 c\u00f9ng l\u00fac.',
  'C\u00fa ph\u00e1p t\u1ed1t nh\u1ea5t: \u0111\u1ed9ng t\u1eeb + \u0111\u1ed1i t\u01b0\u1ee3ng. V\u00ed d\u1ee5: "m\u1edf notepad", "\u0111\u00f3ng chrome".',
  '\u0110i\u1ec1u khi\u1ec3n chu\u1ed9t: "click a1", "click ph\u1ea3i b3", ho\u1eb7c "click 520,340".',
  'K\u00e9o chu\u1ed9t: "k\u00e9o chu\u1ed9t t\u1eeb a1 \u0111\u1ebfn c3" ho\u1eb7c "k\u00e9o chu\u1ed9t t\u1eeb 100,200 \u0111\u1ebfn 300,400".',
  'M\u1edf l\u01b0\u1edbi tham chi\u1ebfu: "hi\u1ec3n th\u1ecb l\u01b0\u1edbi t\u1ecda \u0111\u1ed9".',
  'G\u00f5 ch\u1eef: "g\u00f5 ch\u1eef Xin ch\u00e0o", ph\u00edm t\u1eaft: "nh\u1ea5n ph\u00edm ctrl+s", "ph\u00edm t\u1eaft alt+tab".',
  'T\u1ea1o file m\u1ecdi \u0111\u1ecbnh d\u1ea1ng: "t\u1ea1o file bao_cao.docx", "t\u1ea1o file du_lieu.xlsx".',
  'L\u01b0u thao t\u00e1c ngay trong chat: "th\u00eam thao t\u00e1c di chu\u1ed9t l\u00ean 3 b\u01b0\u1edbc v\u00e0 click".',
  'N\u1ebfu t\u00ean app d\u1ec5 sai, h\u00e3y nh\u1eadp g\u1ea7n \u0111\u00fang: h\u1ec7 th\u1ed1ng s\u1ebd g\u1ee3i \u00fd t\u00ean \u1ee9ng d\u1ee5ng g\u1ea7n nh\u1ea5t.',
  'D\u00f9ng "Tr\u00f2 chuy\u1ec7n m\u1edbi" khi \u0111\u1ed5i ch\u1ee7 \u0111\u1ec1 \u0111\u1ec3 AI ph\u1ea3n h\u1ed3i ch\u00ednh x\u00e1c h\u01a1n.',
];
const COMMAND_GUIDE_SECTIONS = [
  {
    title: 'Chat v\u00e0 gi\u1ecdng n\u00f3i',
    items: [
      'Tr\u00f2 chuy\u1ec7n th\u01b0\u1eddng: nh\u1eadp c\u00e2u h\u1ecfi b\u1ea5t k\u1ef3 trong \u00f4 chat.',
      'Xem h\u01b0\u1edbng d\u1eabn nhanh ngay trong chat: "tip", "tips", "h\u01b0\u1edbng d\u1eabn", "l\u1ec7nh \u0111i\u1ec1u khi\u1ec3n".',
      'B\u1eadt nh\u1eadp prompt b\u1eb1ng gi\u1ecdng n\u00f3i: "kh\u1edfi \u0111\u1ed9ng nh\u1eadp gi\u1ecdng n\u00f3i".',
      'T\u1eaft nh\u1eadp prompt b\u1eb1ng gi\u1ecdng n\u00f3i: "k\u1ebft th\u00fac nh\u1eadp gi\u1ecdng n\u00f3i".',
      'B\u1eadt \u0111\u1ecdc ph\u1ea3n h\u1ed3i: "b\u1eadt gi\u1ecdng \u0111\u1ecdc" ho\u1eb7c "b\u1eadt \u0111\u1ecdc".',
      'T\u1eaft \u0111\u1ecdc ph\u1ea3n h\u1ed3i: "t\u1eaft gi\u1ecdng \u0111\u1ecdc", "t\u1eaft \u0111\u1ecdc", "im l\u1eb7ng".',
    ],
  },
  {
    title: '\u1ee8ng d\u1ee5ng',
    items: [
      'M\u1edf \u1ee9ng d\u1ee5ng: "m\u1edf chrome", "m\u1edf \u1ee9ng d\u1ee5ng steam".',
      'T\u00ecm \u1ee9ng d\u1ee5ng tr\u00ean m\u00e1y: "t\u00ecm \u1ee9ng d\u1ee5ng steam", "t\u00ecm app zalo".',
      '\u0110\u00f3ng \u1ee9ng d\u1ee5ng: "\u0111\u00f3ng chrome", "t\u1eaft app edge", "\u0111\u00f3ng \u1ee9ng d\u1ee5ng notepad".',
      'M\u1edf web: "m\u1edf web openai.com", "m\u1edf website github.com".',
    ],
  },
  {
    title: 'Chu\u1ed9t v\u00e0 b\u00e0n ph\u00edm',
    items: [
      'Click tr\u00e1i: "click a1", "click 520,340".',
      'Click ph\u1ea3i: "click ph\u1ea3i b3".',
      'K\u00e9o chu\u1ed9t: "k\u00e9o chu\u1ed9t t\u1eeb a1 \u0111\u1ebfn c3", "k\u00e9o chu\u1ed9t t\u1eeb 100,200 \u0111\u1ebfn 300,400".',
      'M\u1edf l\u01b0\u1edbi t\u1ecda \u0111\u1ed9: "hi\u1ec3n th\u1ecb l\u01b0\u1edbi t\u1ecda \u0111\u1ed9".',
      'Cu\u1ed9n chu\u1ed9t: "cu\u1ed9n l\u00ean", "cu\u1ed9n xu\u1ed1ng".',
      'G\u00f5 ch\u1eef: "g\u00f5 ch\u1eef Xin ch\u00e0o".',
      'Nh\u1ea5n ph\u00edm: "nh\u1ea5n ph\u00edm ctrl+s", "ph\u00edm t\u1eaft alt+tab".',
      'L\u01b0u thao t\u00e1c m\u1edbi: "th\u00eam thao t\u00e1c di chu\u1ed9t l\u00ean 3 b\u01b0\u1edbc v\u00e0 click".',
    ],
  },
  {
    title: 'File v\u00e0 th\u01b0 m\u1ee5c Desktop',
    items: [
      'Li\u1ec7t k\u00ea Desktop: "li\u1ec7t k\u00ea desktop", "xem desktop".',
      'M\u1edf/\u0111\u1ecdc file: "m\u1edf file ghi_chu.txt", "xem file bao_cao.docx".',
      'Li\u1ec7t k\u00ea th\u01b0 m\u1ee5c: "li\u1ec7t k\u00ea th\u01b0 m\u1ee5c Downloads".',
      'T\u1ea1o file: "t\u1ea1o file bao_cao.docx", "t\u1ea1o file du_lieu.xlsx".',
      'Ghi file: "ghi file ghi_chu.txt: n\u1ed9i dung m\u1edbi", "ghi \u0111\u00e8 file ghi_chu.txt n\u1ed9i dung h\u00f4m nay".',
      'Th\u00eam v\u00e0o file: "th\u00eam v\u00e0o file ghi_chu.txt d\u00f2ng m\u1edbi".',
      'T\u1ea1o/x\u00f3a th\u01b0 m\u1ee5c: "t\u1ea1o th\u01b0 m\u1ee5c test", "x\u00f3a th\u01b0 m\u1ee5c test".',
      'X\u00f3a file/\u0111\u01b0\u1eddng d\u1eabn: "x\u00f3a file ghi_chu.txt", "x\u00f3a \u0111\u01b0\u1eddng d\u1eabn tmp/test".',
    ],
  },
  {
    title: 'Ti\u1ec7n \u00edch',
    items: [
      'Ki\u1ec3m tra \u0111\u1ed3ng h\u1ed3 desktop: "th\u1ef1c hi\u1ec7n t\u00e1c v\u1ee5: ki\u1ec3m tra th\u1eddi gian".',
      'Ch\u1edd: "ch\u1edd 1.5".',
      'M\u1edf file d\u1ef1 \u00e1n \u0111i\u1ec1u khi\u1ec3n: "m\u1edf file train", "xem l\u1ecbch s\u1eed h\u1ed9i tho\u1ea1i", "li\u1ec7t k\u00ea model".',
    ],
  },
];
const TIP_COMMANDS = new Set([
  'tip',
  'tips',
  'huong dan',
  'huong dan nhanh',
  'huong dan su dung',
  'huong dan dieu khien',
  'lenh dieu khien',
  'dieu khien may tinh',
]);
const SAVE_ACTION_COMMAND_PATTERN = /^\s*(?:thêm|them|lưu|luu|cấu hình|cau hinh)\s+(?:thao tác|thao tac|lệnh|lenh|câu lệnh|cau lenh)\s+(.+?)\s*$/iu;
const getSaveActionBody = (value) => {
  const text = String(value || '').trim();
  if (!text) return '';
  const matched = text.match(SAVE_ACTION_COMMAND_PATTERN);
  return matched ? String(matched[1] || '').trim() : '';
};

const toChatHistory = (history) =>
  history
    .slice(-28)
    .filter((item) => {
      const sender = String(item?.sender || '');
      const text = String(item?.text || '');
      if (!sender || !text.trim()) return false;
      if (sender === 'bot') {
        const norm = String(text || '')
          .toLowerCase()
          .replace(/đ/g, 'd')
          .normalize('NFD')
          .replace(/\p{M}/gu, '')
          .replace(/[^a-z0-9\s]/g, ' ')
          .replace(/\s+/g, ' ')
          .trim();
        if (norm.includes('da thuc thi tap lenh train') || norm.includes('thc thi tp lnh train')) {
          return false;
        }
      }
      return true;
    })
    .slice(-16)
    .map((item) => ({
      sender: item.sender,
      text: item.text,
    }));

const estimateTokenCount = (value) => {
  const text = String(value || '').trim();
  if (!text) return 0;
  return Math.max(1, Math.round(text.length / 4));
};

const normalizeVoiceCommand = (value) => String(value || '')
  .toLowerCase()
  .replace(/đ/g, 'd')
  .normalize('NFD')
  .replace(/\p{M}/gu, '')
  .replace(/[^a-z0-9\s]/g, ' ')
  .replace(/\s+/g, ' ')
  .trim();

const includesAny = (text, phrases) => phrases.some((phrase) => text.includes(phrase));
const hasCoordinateGridKeyword = (normalizedText) =>
  includesAny(normalizedText, [
    'luoi toa do',
    'toa do',
    'to do',
    'luoi chuot',
    'grid',
  ]);
const isTipsCommand = (normalizedText) =>
  TIP_COMMANDS.has(normalizedText) ||
  includesAny(normalizedText, ['xem tip', 'xem huong dan', 'hien huong dan', 'goi y lenh']);
const isCoordinateGridCommand = (normalizedText) =>
  !includesAny(normalizedText, ['an ', 'tat ', 'dong ', 'hide ']) && includesAny(normalizedText, [
    'hien thi luoi toa do',
    'mo luoi toa do',
    'xem luoi toa do',
    'luoi toa do',
    'toa do chuot',
    'luoi chuot',
  ]);
const isHideCoordinateGridCommand = (normalizedText) =>
  includesAny(normalizedText, [
    'an luoi toa do',
    'tat luoi toa do',
    'dong luoi toa do',
    'hide luoi toa do',
    'an luoi chuot',
    'tat luoi chuot',
    'dong luoi chuot',
  ]) || (
    hasCoordinateGridKeyword(normalizedText)
    && includesAny(normalizedText, ['an', 'tat', 'dong', 'hide'])
  );
const shouldAutoOpenCoordinateGrid = (normalizedText) =>
  includesAny(normalizedText, [
    'keo chuot',
    'drag mouse',
    'drag ',
    'click ',
    'click phai',
    'di chuot',
    'move chuot',
  ]);
const buildTipsMessage = () => `H\u01b0\u1edbng d\u1eabn \u0111i\u1ec1u khi\u1ec3n nhanh:\n${QUICK_TIPS.map((tip, index) => `${index + 1}. ${tip}`).join('\n')}`;
const stripControlChars = (value) =>
  Array.from(String(value || ''))
    .filter((ch) => {
      if (ch === '\n' || ch === '\r' || ch === '\t') return true;
      const code = ch.charCodeAt(0);
      return !(code <= 31 || code === 127);
    })
    .join('');

const isStartVoicePromptCommand = (normalizedText) => {
  if (!normalizedText) return false;
  if (includesAny(normalizedText, START_VOICE_STANDBY_COMMANDS)) return true;
  const hasStartVerb = includesAny(normalizedText, ['khoi dong', 'bat dau', 'kich hoat', 'bat']);
  const hasVoiceNoun = includesAny(normalizedText, ['giong noi', 'nhap giong', 'voice']);
  return hasStartVerb && hasVoiceNoun;
};

const isStopVoicePromptCommand = (normalizedText) => {
  if (!normalizedText) return false;
  if (includesAny(normalizedText, STOP_VOICE_STANDBY_COMMANDS)) return true;
  const hasStopVerb = includesAny(normalizedText, ['ket thuc', 'dung', 'tat', 'ngung']);
  const hasVoiceNoun = includesAny(normalizedText, ['giong noi', 'nhap giong', 'voice']);
  return hasStopVerb && hasVoiceNoun;
};

const isStopVoiceResponseCommand = (normalizedText) => {
  if (!normalizedText) return false;
  if (includesAny(normalizedText, STOP_VOICE_RESPONSE_COMMANDS)) return true;
  return includesAny(normalizedText, ['tat', 'dung', 'ngung']) && includesAny(normalizedText, ['giong doc', 'doc phan hoi']);
};

const isStartVoiceResponseCommand = (normalizedText) => {
  if (!normalizedText) return false;
  if (includesAny(normalizedText, START_VOICE_RESPONSE_COMMANDS)) return true;
  return includesAny(normalizedText, ['bat', 'khoi dong']) && includesAny(normalizedText, ['giong doc', 'doc phan hoi']);
};

const repairLikelyMojibake = (value) => {
  const text = String(value || '');
  if (!text) return '';
  const hasMojibakeMarker = /(?:\u00C3.|\u00C4.|\u00C2.|\u00E1\u00BA|\u00E1\u00BB|\u00E2\u20AC|\uFFFD)/u.test(text);
  if (!hasMojibakeMarker) return text;

  try {
    const bytes = [];
    for (let i = 0; i < text.length; i += 1) {
      const code = text.charCodeAt(i);
      if (code > 255) {
        return text;
      }
      bytes.push(code);
    }
    const decoded = new TextDecoder('utf-8').decode(new Uint8Array(bytes));
    if (!decoded) return text;

    const rawBad = (text.match(/(?:\u00C3.|\u00C4.|\u00C2.|\u00E1\u00BA|\u00E1\u00BB|\u00E2\u20AC|\uFFFD)/gu) || []).length;
    const fixedBad = (decoded.match(/(?:\u00C3.|\u00C4.|\u00C2.|\u00E1\u00BA|\u00E1\u00BB|\u00E2\u20AC|\uFFFD)/gu) || []).length;
    if (fixedBad < rawBad) {
      return decoded;
    }
  } catch (_error) {
    return text;
  }

  return text;
};
const sanitizeDisplayText = (value) => {
  const text = String(value || '');
  return stripControlChars(text)
    .replace(/[ \t]{2,}/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
};

const normalizeAnswerText = (value) => {
  let text = (value || '')
    .replace(/\*\*/g, '')
    .replace(/`/g, '')
    .replace(/\r\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();

  text = repairLikelyMojibake(text);

  text = sanitizeDisplayText(text);
  text = text.normalize('NFC');

  if (text.length > 1400) {
    text = `${text.slice(0, 1400).trimEnd()}...`;
  }
  return text;
};

const isLikelyControlPrompt = (normalizedPrompt) => {
  if (!normalizedPrompt) return false;
  return includesAny(normalizedPrompt, [
    'mo ',
    'dong ',
    'tat app',
    'dong ung dung',
    'open app',
    'close app',
    'open file',
    'read file',
    'list dir',
    'tao file',
    'xoa file',
    'xoa thu muc',
  ]);
};

const isControlLeakAnswer = (normalizedAnswer) =>
  includesAny(normalizedAnswer, [
    'da thuc thi tap lenh train',
    'thc thi tp lnh train',
    'da mo ung dung',
    'm ng dng',
  ]);

const isFallbackOrErrorAnswer = (rawAnswer) => {
  const normalized = normalizeVoiceCommand(rawAnswer);
  if (!normalized) return false;

  if (
    includesAny(normalized, [
      'khong ket noi duoc dich vu ai',
      'tam thoi chua co cau tra loi phu hop',
      'he thong ai dang ban khoi dong hoac tam thoi qua tai',
      'he thong ai dang ban khoi dong',
      'tam thoi qua tai',
      'hien tai minh chua tim duoc cau tra loi phu hop',
    ])
  ) {
    return true;
  }

  // Các câu cực ngắn, quá chung chung cũng không nên đem đi train tự động
  if (normalized.length <= 32) {
    const trivialPatterns = ['khong biet', 'khong ro', 'khong chac', 'khong co thong tin'];
    if (includesAny(normalized, trivialPatterns)) return true;
  }

  return false;
};

const extractAudioUrl = (payload) => {
  if (!payload || typeof payload !== 'object') return '';

  const candidatePaths = [
    payload.audio_url,
    payload.audioUrl,
    payload.url,
    payload.result?.audio_url,
    payload.result?.audioUrl,
    payload.result?.url,
    payload.data?.audio_url,
    payload.data?.audioUrl,
    payload.data?.url,
  ];

  const found = candidatePaths.find((value) => typeof value === 'string' && value.trim());
  return found ? found.trim() : '';
};

const createSessionId = () => `sess-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;

const getOrCreateSessionId = (username) => {
  if (typeof window === 'undefined') {
    return 'default-web-session';
  }

  const key = `${SESSION_KEY_PREFIX}:${username || 'guest'}`;
  const existing = (window.localStorage.getItem(key) || '').trim();
  if (existing) {
    return existing;
  }

  const created = createSessionId();
  window.localStorage.setItem(key, created);
  return created;
};

const setSessionIdForUser = (username, sessionId) => {
  if (typeof window === 'undefined') return;
  const key = `${SESSION_KEY_PREFIX}:${username || 'guest'}`;
  window.localStorage.setItem(key, sessionId);
};

const pickVietnameseVoice = (voices) => {
  if (!Array.isArray(voices) || !voices.length) {
    return null;
  }

  const normalized = voices.map((voice) => ({
    voice,
    key: `${voice.name} ${voice.lang}`.toLowerCase(),
    isVietnamese: String(voice.lang || '').toLowerCase().startsWith('vi'),
  }));

  const vietnameseVoices = normalized.filter((item) => item.isVietnamese);
  const isLikelyMale = (key) => MALE_VOICE_HINTS.some((hint) => key.includes(hint));
  const preferredVietnameseFemale = vietnameseVoices.find(
    (item) => FEMALE_VOICE_HINTS.some((hint) => item.key.includes(hint)) && !isLikelyMale(item.key),
  );
  if (preferredVietnameseFemale) {
    return preferredVietnameseFemale.voice;
  }

  const likelyFemaleVietnamese = vietnameseVoices.find(
    (item) => !isLikelyMale(item.key),
  );
  if (likelyFemaleVietnamese) {
    return likelyFemaleVietnamese.voice;
  }

  const fallbackVietnamese = vietnameseVoices[0];
  if (fallbackVietnamese) {
    return fallbackVietnamese.voice;
  }

  const preferredFemaleAnyLang = normalized.find(
    (item) => FEMALE_VOICE_HINTS.some((hint) => item.key.includes(hint)) && !isLikelyMale(item.key),
  );
  if (preferredFemaleAnyLang) {
    return preferredFemaleAnyLang.voice;
  }

  return normalized[0]?.voice || null;
};

const LoadingDots = () => (
  <div className={styles.loadingDots}>
    <div className={styles.dot}></div>
    <div className={styles.dot}></div>
    <div className={styles.dot}></div>
  </div>
);

const AnimeCompanion = ({ expression, isSpeaking, isRecording, useImageModel, onImageError }) => (
  <div className={styles.animeScene}>
    <div className={`${styles.animeAura} ${isSpeaking ? styles.animeAuraSpeaking : ''}`}></div>
    {useImageModel ? (
      <div className={styles.animeImageWrap}>
        <img
          src={ANIME_MODEL_IMAGE_PATH}
          alt={'Tr\u1ee3 l\u00fd anime'}
          className={styles.animeImage}
          onError={onImageError}
        />
      </div>
    ) : (
      <div className={`${styles.animeGirl} ${isSpeaking ? styles.animeGirlSpeaking : ''} ${isRecording ? styles.animeGirlListening : ''}`}>
        <div className={styles.animeHair}></div>
        <div className={styles.animeFace} data-expression={expression.key}>
          <div className={styles.animeEyes}>
            <span className={`${styles.eyeDot} ${styles.leftEye}`}></span>
            <span className={`${styles.eyeDot} ${styles.rightEye}`}></span>
          </div>
          <div className={styles.animeMouth}></div>
        </div>
        <div className={styles.animeBody}></div>
      </div>
    )}

    <div className={styles.modelPlaceholder}>
      {isRecording ? '\u0110ang l\u1eafng nghe l\u1ec7nh...' : `Tr\u1ee3 l\u00fd - ${expression.mood}`}
    </div>
  </div>
);

const SettingsPopover = ({ userData, handleAction, isSettingsOpen, isAdmin }) => (
  <div className={`${styles.settingsPopover} ${isSettingsOpen ? styles.active : ''}`}>
    <p className="text-gray-400 text-sm mb-3">
      **{userData.name}** ({userData.email})
    </p>
    <hr className="border-gray-700 mb-2" />

    <div className={styles.popoverItem} onClick={() => handleAction('profile')}>
      <User size={16} style={{ marginRight: '10px' }} />
      {'Th\u00f4ng tin t\u00e0i kho\u1ea3n'}
    </div>
    <div className={styles.popoverItem} onClick={() => handleAction('privacy')}>
      <Lock size={16} style={{ marginRight: '10px' }} />
      {'Thay \u0111\u1ed5i quy\u1ec1n ri\u00eang t\u01b0'}
    </div>
    <div className={styles.popoverItem} onClick={() => handleAction('guide')}>
      <BookOpen size={16} style={{ marginRight: '10px' }} />
      {'H\u01b0\u1edbng d\u1eabn l\u1ec7nh'}
    </div>
    <div className={styles.popoverItem} onClick={() => handleAction('gridShow')}>
      <Grid3X3 size={16} style={{ marginRight: '10px' }} />
      {'Hi\u1ec7n l\u01b0\u1edbi t\u1ecda \u0111\u1ed9'}
    </div>
    <div className={styles.popoverItem} onClick={() => handleAction('gridHide')}>
      <Grid3X3 size={16} style={{ marginRight: '10px' }} />
      {'\u1ea8n l\u01b0\u1edbi t\u1ecda \u0111\u1ed9'}
    </div>
    <div className={styles.popoverItem} onClick={() => handleAction('train')}>
      <Send size={16} style={{ marginRight: '10px' }} />
      {'Train AI'}
    </div>
    {isAdmin && (
      <div className={styles.popoverItem} onClick={() => handleAction('admin')}>
        <Shield size={16} style={{ marginRight: '10px' }} />
        {'Trang qu\u1ea3n tr\u1ecb'}
      </div>
    )}
    <div className={styles.popoverItem} onClick={() => handleAction('delete')}>
      <Trash2 size={16} style={{ marginRight: '10px' }} />
      {'X\u00f3a t\u00e0i kho\u1ea3n (Nguy hi\u1ec3m)'}
    </div>
    <div className={`${styles.popoverItem} ${styles.logout}`} onClick={() => handleAction('logout')}>
      <LogOut size={16} style={{ marginRight: '10px' }} />
      {'\u0110\u0103ng xu\u1ea5t'}
    </div>
  </div>
);

const TrainModal = ({
  isOpen,
  question,
  answer,
  isSubmitting,
  onQuestionChange,
  onAnswerChange,
  onClose,
  onSubmit,
}) => {
  if (!isOpen) return null;
  return (
    <div className={styles.trainOverlay}>
      <div className={styles.trainModal}>
        <div className={styles.trainHeader}>
          <h3>{'Train AI Theo Y\u0301 Ba\u0323n'}</h3>
          <button type="button" className={styles.trainCloseButton} onClick={onClose} disabled={isSubmitting}>
            {'\u0110o\u0301ng'}
          </button>
        </div>
        <p className={styles.trainHint}>
          {'Nh\u1eadp c\u00e2u h\u1ecfi v\u00e0 c\u00e2u tr\u1ea3 l\u1eddi m\u1eabu \u0111\u1ec3 AI hi\u1ec3u theo ng\u1eef c\u1ea3nh b\u1ea1n mu\u1ed1n.'}
        </p>
        <form onSubmit={onSubmit} className={styles.trainForm}>
          <label className={styles.trainLabel}>
            {'C\u00e2u h\u1ecfi'}
            <textarea
              className={styles.trainTextarea}
              value={question}
              onChange={(event) => onQuestionChange(event.target.value)}
              rows={3}
              maxLength={1000}
              placeholder={'V\u00ed d\u1ee5: Quy tr\u00ecnh xin ngh\u1ec9 ph\u00e9p \u1edf c\u00f4ng ty m\u00ecnh?'}
              disabled={isSubmitting}
              required
            />
          </label>
          <label className={styles.trainLabel}>
            {'C\u00e2u tr\u1ea3 l\u1eddi m\u1eabu'}
            <textarea
              className={styles.trainTextarea}
              value={answer}
              onChange={(event) => onAnswerChange(event.target.value)}
              rows={6}
              maxLength={3000}
              placeholder={'V\u00ed d\u1ee5: B\u1ea1n t\u1ea1o \u0111\u01a1n tr\u00ean portal n\u1ed9i b\u1ed9, g\u1eedi tr\u01b0\u1edfng nh\u00f3m duy\u1ec7t tr\u01b0\u1edbc 17h.'}
              disabled={isSubmitting}
              required
            />
          </label>
          <div className={styles.trainActions}>
            <button type="button" className={styles.trainSecondaryButton} onClick={onClose} disabled={isSubmitting}>
              {'H\u1ee7y'}
            </button>
            <button type="submit" className={styles.trainPrimaryButton} disabled={isSubmitting || !question.trim() || !answer.trim()}>
              {isSubmitting ? '\u0110ang l\u01b0u...' : 'L\u01b0u d\u1eef li\u1ec7u train'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const CommandSaveProgressModal = ({ isOpen, progress, stageText }) => {
  if (!isOpen) return null;
  const safeProgress = Math.max(0, Math.min(100, Number(progress) || 0));
  return (
    <div className={styles.trainOverlay}>
      <div className={styles.commandSaveModal}>
        <div className={styles.commandSaveHeader}>
          <h3>{'Đang lưu cấu hình thao tác'}</h3>
          <span className={styles.commandSavePercent}>{`${safeProgress}%`}</span>
        </div>
        <p className={styles.commandSaveHint}>{stageText || 'Đang xử lý yêu cầu...'}</p>
        <div className={styles.commandSaveProgressTrack}>
          <div className={styles.commandSaveProgressBar} style={{ width: `${safeProgress}%` }}></div>
        </div>
      </div>
    </div>
  );
};

const CommandGuideModal = ({
  isOpen,
  isLoading,
  error,
  rules,
  sections,
  onClose,
}) => {
  if (!isOpen) return null;

  const triggerLabels = Array.isArray(rules)
    ? rules
      .map((rule) => String(rule?.trigger_display || '').trim())
      .filter(Boolean)
    : [];

  return (
    <div className={styles.trainOverlay}>
      <div className={styles.guideModal}>
        <div className={styles.guideHeader}>
          <div>
            <h3>{'H\u01b0\u1edbng d\u1eabn l\u1ec7nh AIPA'}</h3>
            <p>{'Danh s\u00e1ch l\u1ec7nh ng\u01b0\u1eddi d\u00f9ng c\u00f3 th\u1ec3 g\u1ecdi tr\u1ef1c ti\u1ebfp trong chat.'}</p>
          </div>
          <button type="button" className={styles.trainCloseButton} onClick={onClose}>
            {'\u0110\u00f3ng'}
          </button>
        </div>

        <div className={styles.guideBody}>
          {sections.map((section) => (
            <section key={section.title} className={styles.guideSection}>
              <h4>{section.title}</h4>
              <ul className={styles.guideList}>
                {section.items.map((item, index) => (
                  <li key={`${section.title}-${index}`}>{item}</li>
                ))}
              </ul>
            </section>
          ))}

          <section className={styles.guideSection}>
            <h4>{'Trigger \u0111i\u1ec1u khi\u1ec3n \u0111ang c\u1ea5u h\u00ecnh'}</h4>
            {isLoading ? (
              <p className={styles.guideMeta}>{'\u0110ang t\u1ea3i danh s\u00e1ch l\u1ec7nh...'}</p>
            ) : error ? (
              <p className={styles.guideError}>{error}</p>
            ) : triggerLabels.length ? (
              <>
                <p className={styles.guideMeta}>
                  {`Hi\u1ec7n c\u00f3 ${triggerLabels.length} trigger c\u00f3 th\u1ec3 g\u1ecdi tr\u1ef1c ti\u1ebfp trong chat.`}
                </p>
                <div className={styles.guideRuleGrid}>
                  {triggerLabels.map((label) => (
                    <span key={label} className={styles.guideRuleItem}>{label}</span>
                  ))}
                </div>
              </>
            ) : (
              <p className={styles.guideMeta}>{'Ch\u01b0a c\u00f3 trigger n\u00e0o \u0111\u01b0\u1ee3c c\u1ea5u h\u00ecnh.'}</p>
            )}
          </section>
        </div>
      </div>
    </div>
  );
};

const HomePage = () => {
  const navigate = useNavigate();
  const { currentUser, auth, logout } = useAuth();
  const isAdmin = auth?.role === 'ROLE_ADMIN';

  const username = currentUser?.username || 'Ng\u01b0\u1eddi d\u00f9ng';
  const userData = {
    name: username,
    email: currentUser?.email || `${username}@local`,
  };

  const [messages, setMessages] = useState([
    { id: 1, sender: 'bot', text: getWelcomeText(username) },
  ]);
  const [input, setInput] = useState('');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isBotTyping, setIsBotTyping] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [availableVoices, setAvailableVoices] = useState([]);
  const [expression, setExpression] = useState(() => getExpressionByKey('smile'));
  const [hasModelImageError, setHasModelImageError] = useState(false);
  const [userSettings, setUserSettings] = useState(() => getUserSettings(username));
  const [isVoicePromptMode, setIsVoicePromptMode] = useState(false);
  const [isTrainModalOpen, setIsTrainModalOpen] = useState(false);
  const [isTipsOpen, setIsTipsOpen] = useState(false);
  const [isCommandGuideOpen, setIsCommandGuideOpen] = useState(false);
  const [isLoadingCommandGuide, setIsLoadingCommandGuide] = useState(false);
  const [commandGuideError, setCommandGuideError] = useState('');
  const [commandGuideRules, setCommandGuideRules] = useState([]);
  const [trainQuestion, setTrainQuestion] = useState('');
  const [trainAnswer, setTrainAnswer] = useState('');
  const [isSubmittingTrain, setIsSubmittingTrain] = useState(false);
  const [isSavingControlCommand, setIsSavingControlCommand] = useState(false);
  const [saveControlCommandProgress, setSaveControlCommandProgress] = useState(0);
  const [saveControlCommandStage, setSaveControlCommandStage] = useState('');
  const isVoiceMicEnabled = Boolean(userSettings.voiceChatEnabled);
  const isVoiceResponseEnabled = userSettings.aiResponseVoiceEnabled !== false;

  const chatAreaRef = useRef(null);
  const expressionTimerRef = useRef(null);
  const sessionIdRef = useRef(getOrCreateSessionId(username));
  const recognitionRef = useRef(null);
  const currentAudioRef = useRef(null);
  const audioObjectUrlRef = useRef('');
  const handleBotResponseRef = useRef(null);
  const speechSupportNotifiedRef = useRef(false);
  const micPermissionDeniedNotifiedRef = useRef(false);
  const saveControlProgressTimerRef = useRef(null);

  const stopCurrentSpeechOutput = useCallback(() => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current.src = '';
      currentAudioRef.current = null;
    }

    if (audioObjectUrlRef.current && typeof window !== 'undefined') {
      window.URL.revokeObjectURL(audioObjectUrlRef.current);
      audioObjectUrlRef.current = '';
    }

    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }

    setIsSpeaking(false);
  }, []);

  const pushBotMessage = useCallback((text) => {
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now() + Math.floor(Math.random() * 1000),
        sender: 'bot',
        text,
      },
    ]);
  }, []);

  const stopSaveControlProgress = useCallback(() => {
    if (saveControlProgressTimerRef.current) {
      window.clearInterval(saveControlProgressTimerRef.current);
      saveControlProgressTimerRef.current = null;
    }
  }, []);

  const closeSaveControlDialog = useCallback(() => {
    stopSaveControlProgress();
    setIsSavingControlCommand(false);
    setSaveControlCommandProgress(0);
    setSaveControlCommandStage('');
  }, [stopSaveControlProgress]);

  const closeCommandGuide = useCallback(() => {
    setIsCommandGuideOpen(false);
  }, []);

  const openCommandGuide = useCallback(async () => {
    setIsCommandGuideOpen(true);
    setIsLoadingCommandGuide(true);
    setCommandGuideError('');
    try {
      const payload = await fetchComputerControlRulesApi();
      const rules = Array.isArray(payload?.rules) ? payload.rules : [];
      setCommandGuideRules(rules);
    } catch (error) {
      setCommandGuideRules([]);
      setCommandGuideError(String(error?.message || '').trim() || 'Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c danh s\u00e1ch l\u1ec7nh \u0111i\u1ec1u khi\u1ec3n.');
    } finally {
      setIsLoadingCommandGuide(false);
    }
  }, []);

  const showDesktopCoordinateGrid = useCallback(async ({ announce = true, focus = '' } = {}) => {
    try {
      await showComputerControlOverlayApi({ focus });
      if (announce) {
        pushBotMessage('Đã hiển thị lưới tọa độ trực tiếp trên màn hình. Bạn có thể nói: "kéo chuột từ 100,200 đến 300,400" hoặc "kéo chuột từ a1 đến c3".');
      }
      return true;
    } catch (error) {
      if (announce) {
        pushBotMessage(String(error?.message || '').trim() || 'Không hiển thị được lưới tọa độ trên màn hình.');
      }
      return false;
    }
  }, [pushBotMessage]);

  const hideDesktopCoordinateGrid = useCallback(async (announce = true) => {
    try {
      await hideComputerControlOverlayApi();
      if (announce) {
        pushBotMessage('Đã ẩn lưới tọa độ trên màn hình.');
      }
      return true;
    } catch (error) {
      if (announce) {
        pushBotMessage(String(error?.message || '').trim() || 'Không ẩn được lưới tọa độ lúc này.');
      }
      return false;
    }
  }, [pushBotMessage]);

  const startSaveControlProgress = useCallback(() => {
    stopSaveControlProgress();
    setIsSavingControlCommand(true);
    setSaveControlCommandProgress(8);
    setSaveControlCommandStage('Đang phân tích câu lệnh chat...');
    let currentProgress = 8;
    saveControlProgressTimerRef.current = window.setInterval(() => {
      currentProgress = Math.min(92, currentProgress + (currentProgress < 40 ? 12 : currentProgress < 70 ? 8 : 4));
      setSaveControlCommandProgress(currentProgress);
      if (currentProgress < 35) {
        setSaveControlCommandStage('Đang chuyển câu lệnh thành thao tác hệ thống...');
      } else if (currentProgress < 75) {
        setSaveControlCommandStage('Đang lưu cấu hình thao tác vào máy...');
      } else {
        setSaveControlCommandStage('Đang hoàn tất cấu hình...');
      }
    }, 220);
  }, [stopSaveControlProgress]);

  useEffect(() => () => {
    if (saveControlProgressTimerRef.current) {
      window.clearInterval(saveControlProgressTimerRef.current);
      saveControlProgressTimerRef.current = null;
    }
  }, []);

  const stopVoiceRecognition = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.onresult = null;
      recognitionRef.current.onerror = null;
      recognitionRef.current.onend = null;
      try {
        recognitionRef.current.stop();
      } catch (_error) {
        // Ignore stop errors when recognition already stopped.
      }
      recognitionRef.current = null;
    }
    setIsRecording(false);
  }, []);

  useEffect(() => {
    sessionIdRef.current = getOrCreateSessionId(username);
    setUserSettings(getUserSettings(username));
    setIsVoicePromptMode(false);
    speechSupportNotifiedRef.current = false;
    micPermissionDeniedNotifiedRef.current = false;
    setMessages((prev) => {
      if (!prev.length) return prev;
      const first = prev[0];
      if (first.sender !== 'bot') return prev;
      return [
        { ...first, text: getWelcomeText(username) },
        ...prev.slice(1),
      ];
    });
  }, [username]);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const syncSettings = () => setUserSettings(getUserSettings(username));
    window.addEventListener('focus', syncSettings);
    window.addEventListener('storage', syncSettings);
    return () => {
      window.removeEventListener('focus', syncSettings);
      window.removeEventListener('storage', syncSettings);
    };
  }, [username]);

  useEffect(() => {
    if (chatAreaRef.current) {
      chatAreaRef.current.scrollTop = chatAreaRef.current.scrollHeight;
    }
  }, [messages, isBotTyping]);

  useEffect(() => {
    if (typeof window === 'undefined' || !window.speechSynthesis) {
      return undefined;
    }

    const loadVoices = () => {
      const voices = window.speechSynthesis.getVoices();
      setAvailableVoices(Array.isArray(voices) ? voices : []);
    };

    loadVoices();
    window.speechSynthesis.addEventListener('voiceschanged', loadVoices);
    return () => {
      window.speechSynthesis.removeEventListener('voiceschanged', loadVoices);
    };
  }, []);

  useEffect(() => {
    if (expressionTimerRef.current) {
      clearInterval(expressionTimerRef.current);
      expressionTimerRef.current = null;
    }

    if (isSpeaking || isRecording || isBotTyping || isVoicePromptMode) {
      return undefined;
    }
    setExpression((prev) => (prev.key === 'smile' ? prev : getExpressionByKey('smile')));
    return undefined;
  }, [isSpeaking, isRecording, isBotTyping, isVoicePromptMode]);

  useEffect(() => () => {
    if (expressionTimerRef.current) {
      clearInterval(expressionTimerRef.current);
      expressionTimerRef.current = null;
    }
    stopVoiceRecognition();
    stopCurrentSpeechOutput();
  }, [stopVoiceRecognition, stopCurrentSpeechOutput]);

  const toggleVoiceResponse = useCallback((enabled, announce = true) => {
    const nextEnabled = Boolean(enabled);
    patchUserSettings(username, { aiResponseVoiceEnabled: nextEnabled });
    setUserSettings((prev) => ({
      ...prev,
      aiResponseVoiceEnabled: nextEnabled,
    }));

    if (!nextEnabled) {
      stopCurrentSpeechOutput();
      if (announce) {
        pushBotMessage('\u0110\u00e3 t\u1eaft gi\u1ecdng n\u00f3i ph\u1ea3n h\u1ed3i AI.');
      }
      return;
    }

    if (announce) {
      pushBotMessage('\u0110\u00e3 b\u1eadt gi\u1ecdng n\u00f3i ph\u1ea3n h\u1ed3i AI.');
    }
  }, [username, stopCurrentSpeechOutput, pushBotMessage]);

  useEffect(() => {
    if (!isVoiceMicEnabled) {
      setIsVoicePromptMode(false);
      stopVoiceRecognition();
    }
  }, [isVoiceMicEnabled, stopVoiceRecognition]);

  const playTextByVbee = async (text) => {
    if (!isVoiceResponseEnabled || !SHOULD_USE_VBEE_TTS || !text) {
      return false;
    }

    const headers = {
      'Content-Type': 'application/json',
    };

    if (VBEE_TTS_TOKEN) {
      headers.Authorization = `Bearer ${VBEE_TTS_TOKEN}`;
      headers['X-API-KEY'] = VBEE_TTS_TOKEN;
    }

    const payload = {
      app_id: VBEE_TTS_APP_ID || undefined,
      token: VBEE_TTS_TOKEN || undefined,
      voice_code: VBEE_VOICE_CODE,
      text,
      input_text: text,
      format: 'mp3',
      audio_type: 'mp3',
      speed_rate: 1,
      rate: 1,
    };

    try {
      const response = await fetch(VBEE_TTS_URL, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        return false;
      }

      const contentType = String(response.headers.get('content-type') || '').toLowerCase();
      let audioUrl = '';

      if (contentType.includes('audio/')) {
        const audioBlob = await response.blob();
        if (typeof window === 'undefined' || !window.URL) {
          return false;
        }
        if (audioObjectUrlRef.current && typeof window !== 'undefined') {
          window.URL.revokeObjectURL(audioObjectUrlRef.current);
        }
        audioObjectUrlRef.current = window.URL.createObjectURL(audioBlob);
        audioUrl = audioObjectUrlRef.current;
      } else {
        const payloadJson = await response.json().catch(() => ({}));
        audioUrl = extractAudioUrl(payloadJson);
      }

      if (!audioUrl || typeof window === 'undefined') {
        return false;
      }

      const audio = new window.Audio(audioUrl);
      currentAudioRef.current = audio;

      audio.onplay = () => {
        setIsSpeaking(true);
        setExpression(getExpressionByKey('smile'));
      };
      audio.onended = () => {
        setIsSpeaking(false);
      };
      audio.onerror = () => {
        setIsSpeaking(false);
      };

      await audio.play();
      return true;
    } catch (_error) {
      return false;
    }
  };

  const speakText = async (text) => {
    if (!isVoiceResponseEnabled || !text) return;

    stopCurrentSpeechOutput();

    const didPlayVbeeAudio = await playTextByVbee(text);
    if (didPlayVbeeAudio) {
      return;
    }

    if (typeof window === 'undefined' || !window.speechSynthesis) return;

    const profile = FEMALE_VOICE_PROFILE;
    const utterance = new window.SpeechSynthesisUtterance(text);
    utterance.lang = 'vi-VN';
    utterance.rate = profile.rate;
    utterance.pitch = profile.pitch;
    utterance.volume = 1;

    const voices = availableVoices.length ? availableVoices : window.speechSynthesis.getVoices();
    const vietnameseVoice = pickVietnameseVoice(voices);
    if (vietnameseVoice) {
      utterance.voice = vietnameseVoice;
      const selectedLang = String(vietnameseVoice.lang || '').toLowerCase();
      utterance.lang = selectedLang.startsWith('vi') ? vietnameseVoice.lang : 'vi-VN';
    }

    utterance.onstart = () => {
      setIsSpeaking(true);
      setExpression(getExpressionByKey('smile'));
    };
    utterance.onend = () => {
      setIsSpeaking(false);
    };
    utterance.onerror = () => {
      setIsSpeaking(false);
    };

    window.speechSynthesis.speak(utterance);
  };

  const handleBotResponse = async (userPrompt, historySnapshot = [], promptType = 'text') => {
    setIsBotTyping(true);

    let answer = '';
    let requestFailed = false;
    const normalizedPrompt = normalizeVoiceCommand(userPrompt);
    try {
      const response = await chatWithAssistantApi({
        prompt: userPrompt,
        history: toChatHistory(historySnapshot),
        session_id: sessionIdRef.current,
      });
      answer = normalizeAnswerText(response?.answer || '');

      const normalizedAnswer = normalizeVoiceCommand(answer);
      const shouldRetryWithoutHistory = !isLikelyControlPrompt(normalizedPrompt) && isControlLeakAnswer(normalizedAnswer);
      if (shouldRetryWithoutHistory) {
        const retryResponse = await chatWithAssistantApi({
          prompt: userPrompt,
          history: [],
          session_id: sessionIdRef.current,
        });
        answer = normalizeAnswerText(retryResponse?.answer || '');
      }
    } catch (_error) {
      requestFailed = true;
      answer = 'Kh\u00f4ng k\u1ebft n\u1ed1i \u0111\u01b0\u1ee3c d\u1ecbch v\u1ee5 AI.';
    }

    if (!answer) {
      answer = 'T\u1ea1m th\u1eddi ch\u01b0a c\u00f3 c\u00e2u tr\u1ea3 l\u1eddi ph\u00f9 h\u1ee3p.';
    }

    const botResponse = {
      id: Date.now() + 1,
      sender: 'bot',
      text: answer,
    };

    setMessages((prev) => [...prev, botResponse]);
    setExpression(getExpressionByKey('happy'));
    setIsBotTyping(false);

    const storedHistory = appendPromptHistory(username, {
      id: `prompt-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
      type: promptType,
      content: userPrompt,
      createdAt: new Date().toISOString(),
      status: requestFailed ? 'Failed' : 'Completed',
      tokens: estimateTokenCount(userPrompt) + estimateTokenCount(botResponse.text),
    });

    if (
      storedHistory.length > 0 &&
      !requestFailed &&
      userSettings.shareDataForTraining &&
      !isFallbackOrErrorAnswer(botResponse.text)
    ) {
      trainAssistantApi({
        question: userPrompt,
        answer: botResponse.text,
      }).catch(() => undefined);
    }

    if (isVoiceResponseEnabled) {
      const speechText = botResponse.text.length > 350 ? `${botResponse.text.slice(0, 350)}...` : botResponse.text;
      speakText(speechText);
    }
  };

  handleBotResponseRef.current = handleBotResponse;

  const handleSaveControlCommandFromChat = useCallback(async (rawPrompt, actionBody) => {
    const triggerText = String(actionBody || '').trim();
    if (!triggerText) {
      pushBotMessage('Không nhận diện được thao tác cần lưu. Bạn thử lại với mẫu: "thêm thao tác di chuột lên 3 bước và click".');
      return;
    }

    startSaveControlProgress();
    try {
      const result = await saveComputerControlRuleApi({
        prompt: rawPrompt,
        trigger: triggerText,
      });
      stopSaveControlProgress();
      setSaveControlCommandProgress(100);
      setSaveControlCommandStage('Đã lưu cấu hình thành công.');
      await new Promise((resolve) => window.setTimeout(resolve, 350));
      closeSaveControlDialog();

      const savedTrigger = String(result?.trigger_display || triggerText).trim();
      pushBotMessage(`Lưu thao tác thành công. Bạn có thể chat "${savedTrigger}" để chạy lại cấu hình này.`);
    } catch (error) {
      closeSaveControlDialog();
      const message = String(error?.message || '').trim() || 'Không thể lưu cấu hình thao tác lúc này.';
      pushBotMessage(message);
    }
  }, [closeSaveControlDialog, pushBotMessage, startSaveControlProgress, stopSaveControlProgress]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isBotTyping || isSavingControlCommand) return;

    const messageText = input.trim();
    const normalizedMessage = normalizeVoiceCommand(messageText);
    const saveActionBody = getSaveActionBody(messageText);
    const newMessage = { id: Date.now(), sender: 'user', text: messageText };

    if (isTipsCommand(normalizedMessage)) {
      setMessages((prev) => [
        ...prev,
        newMessage,
        { id: Date.now() + 1, sender: 'bot', text: buildTipsMessage() },
      ]);
      setInput('');
      return;
    }

    if (isStopVoiceResponseCommand(normalizedMessage)) {
      setMessages((prev) => [
        ...prev,
        newMessage,
        { id: Date.now() + 1, sender: 'bot', text: '\u0110\u00e3 t\u1eaft gi\u1ecdng n\u00f3i ph\u1ea3n h\u1ed3i AI.' },
      ]);
      setInput('');
      toggleVoiceResponse(false, false);
      return;
    }

    if (isStartVoiceResponseCommand(normalizedMessage)) {
      setMessages((prev) => [
        ...prev,
        newMessage,
        { id: Date.now() + 1, sender: 'bot', text: '\u0110\u00e3 b\u1eadt gi\u1ecdng n\u00f3i ph\u1ea3n h\u1ed3i AI.' },
      ]);
      setInput('');
      toggleVoiceResponse(true, false);
      return;
    }

    if (saveActionBody) {
      setMessages((prev) => [...prev, newMessage]);
      setInput('');
      await handleSaveControlCommandFromChat(messageText, saveActionBody);
      return;
    }

    if (isHideCoordinateGridCommand(normalizedMessage)) {
      setMessages((prev) => [...prev, newMessage]);
      setInput('');
      await hideDesktopCoordinateGrid();
      return;
    }

    if (isCoordinateGridCommand(normalizedMessage)) {
      setMessages((prev) => [...prev, newMessage]);
      setInput('');
      await showDesktopCoordinateGrid();
      return;
    }

    let historySnapshot = [];
    setMessages((prev) => {
      historySnapshot = [...prev, newMessage];
      return historySnapshot;
    });
    setInput('');
    if (shouldAutoOpenCoordinateGrid(normalizedMessage)) {
      void showDesktopCoordinateGrid({ announce: false });
    }
    handleBotResponse(messageText, historySnapshot, 'text');
  };

  const startVoiceStandby = useCallback(() => {
    if (!isVoiceMicEnabled || isBotTyping || isSpeaking) {
      return;
    }
    if (typeof window === 'undefined' || recognitionRef.current) {
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      if (!speechSupportNotifiedRef.current) {
        pushBotMessage('Tr\u00ecnh duy\u1ec7t hi\u1ec7n t\u1ea1i kh\u00f4ng h\u1ed7 tr\u1ee3 nh\u1eadn di\u1ec7n gi\u1ecdng n\u00f3i.');
        speechSupportNotifiedRef.current = true;
      }
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'vi-VN';
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognitionRef.current = recognition;
    setIsRecording(true);
    setExpression(getExpressionByKey('surprised'));

    recognition.onresult = (event) => {
      const parts = [];
      const fromIndex = Number.isInteger(event?.resultIndex) ? event.resultIndex : 0;
      for (let i = fromIndex; i < (event?.results?.length || 0); i += 1) {
        const result = event.results[i];
        if (result?.isFinal) {
          parts.push(result?.[0]?.transcript || '');
        }
      }

      const transcript = parts.join(' ').trim();
      if (!transcript || isBotTyping) {
        return;
      }

      const normalizedTranscript = normalizeVoiceCommand(transcript);
      if (isStopVoiceResponseCommand(normalizedTranscript)) {
        toggleVoiceResponse(false);
        try {
          recognition.stop();
        } catch (_error) {
          // Ignore stop race conditions.
        }
        return;
      }
      if (isStartVoiceResponseCommand(normalizedTranscript)) {
        toggleVoiceResponse(true);
        try {
          recognition.stop();
        } catch (_error) {
          // Ignore stop race conditions.
        }
        return;
      }
      if (isStopVoicePromptCommand(normalizedTranscript)) {
        if (isVoicePromptMode) {
          setIsVoicePromptMode(false);
          pushBotMessage('\u0110\u00e3 k\u1ebft th\u00fac nh\u1eadp gi\u1ecdng n\u00f3i. Mic quay v\u1ec1 ch\u1ebf \u0111\u1ed9 ch\u1edd t\u1eeb k\u00edch ho\u1ea1t.');
        }
        try {
          recognition.stop();
        } catch (_error) {
          // Ignore stop race conditions.
        }
        return;
      }
      if (isStartVoicePromptCommand(normalizedTranscript)) {
        if (!isVoicePromptMode) {
          setIsVoicePromptMode(true);
          pushBotMessage('\u0110\u00e3 kh\u1edfi \u0111\u1ed9ng nh\u1eadp gi\u1ecdng n\u00f3i. B\u1ea1n c\u00f3 th\u1ec3 n\u00f3i prompt.');
        }
        try {
          recognition.stop();
        } catch (_error) {
          // Ignore stop race conditions.
        }
        return;
      }

      if (!isVoicePromptMode) {
        return;
      }

      try {
        recognition.stop();
      } catch (_error) {
        // Ignore stop race conditions.
      }

      const voiceMessage = { id: Date.now(), sender: 'user', text: `Gi\u1ecdng n\u00f3i: ${transcript}` };
      let historySnapshot = [];
      setMessages((prev) => {
        historySnapshot = [...prev, voiceMessage];
        return historySnapshot;
      });
      if (isHideCoordinateGridCommand(normalizedTranscript)) {
        void hideDesktopCoordinateGrid();
        return;
      }
      if (isCoordinateGridCommand(normalizedTranscript)) {
        void showDesktopCoordinateGrid();
        return;
      }
      if (shouldAutoOpenCoordinateGrid(normalizedTranscript)) {
        void showDesktopCoordinateGrid({ announce: false });
      }
      if (handleBotResponseRef.current) {
        handleBotResponseRef.current(transcript, historySnapshot, 'voice');
      }
    };

    recognition.onerror = (event) => {
      if (event?.error === 'aborted' || event?.error === 'no-speech') {
        return;
      }

      if (event?.error === 'not-allowed' || event?.error === 'service-not-allowed') {
        if (!micPermissionDeniedNotifiedRef.current) {
          pushBotMessage('B\u1ea1n ch\u01b0a c\u1ea5p quy\u1ec1n microphone cho tr\u00ecnh duy\u1ec7t.');
          micPermissionDeniedNotifiedRef.current = true;
        }
        stopVoiceRecognition();
        return;
      }

      pushBotMessage('Kh\u00f4ng th\u1ec3 nh\u1eadn di\u1ec7n gi\u1ecdng n\u00f3i. B\u1ea1n th\u1eed l\u1ea1i.');
    };

    recognition.onend = () => {
      recognitionRef.current = null;
      setIsRecording(false);
    };

    try {
      recognition.start();
    } catch (_error) {
      recognitionRef.current = null;
      setIsRecording(false);
    }
  }, [isVoiceMicEnabled, isBotTyping, isSpeaking, pushBotMessage, stopVoiceRecognition, isVoicePromptMode, toggleVoiceResponse, showDesktopCoordinateGrid, hideDesktopCoordinateGrid]);

  useEffect(() => {
    if (!isVoiceMicEnabled || isBotTyping || isSpeaking) {
      if (recognitionRef.current) {
        stopVoiceRecognition();
      }
      return;
    }

    if (!recognitionRef.current && !isRecording) {
      startVoiceStandby();
    }
  }, [isVoiceMicEnabled, isBotTyping, isSpeaking, isRecording, startVoiceStandby, stopVoiceRecognition]);

  const handleSettingsAction = (action) => {
    setIsSettingsOpen(false);

    if (action === 'logout') {
      logout();
      navigate('/', { replace: true });
      return;
    }

    if (action === 'profile') {
      navigate('/userInfo');
      return;
    }

    if (action === 'privacy') {
      navigate('/userInfo?tab=security');
      return;
    }

    if (action === 'guide') {
      openCommandGuide();
      return;
    }

    if (action === 'gridShow') {
      void showDesktopCoordinateGrid();
      return;
    }

    if (action === 'gridHide') {
      void hideDesktopCoordinateGrid();
      return;
    }

    if (action === 'train') {
      setIsTrainModalOpen(true);
      return;
    }

    if (action === 'admin') {
      navigate('/admin');
    }
  };

  const resetTrainForm = useCallback(() => {
    setTrainQuestion('');
    setTrainAnswer('');
  }, []);

  const closeTrainModal = useCallback(() => {
    if (isSubmittingTrain) return;
    setIsTrainModalOpen(false);
  }, [isSubmittingTrain]);

  const handleSubmitTrain = useCallback(async (event) => {
    event.preventDefault();
    const question = trainQuestion.trim();
    const answer = trainAnswer.trim();
    if (!question || !answer || isSubmittingTrain) {
      return;
    }

    setIsSubmittingTrain(true);
    try {
      const result = await trainAssistantApi({ question, answer });
      setIsTrainModalOpen(false);
      resetTrainForm();
      const knowledgeSize = Number(result?.knowledge_size);
      const sizeText = Number.isFinite(knowledgeSize) ? `${knowledgeSize}` : 'nhi\u1ec1u';
      pushBotMessage(`\u0110\u00e3 l\u01b0u d\u1eef li\u1ec7u train th\u00e0nh c\u00f4ng. Kho tri th\u1ee9c hi\u1ec7n c\u00f3 kho\u1ea3ng ${sizeText} m\u1ee5c.`);
    } catch (_error) {
      pushBotMessage('Kh\u00f4ng th\u1ec3 l\u01b0u d\u1eef li\u1ec7u train l\u00fac n\u00e0y. B\u1ea1n th\u1eed l\u1ea1i sau.');
    } finally {
      setIsSubmittingTrain(false);
    }
  }, [trainQuestion, trainAnswer, isSubmittingTrain, pushBotMessage, resetTrainForm]);

  const handleNewConversation = () => {
    stopVoiceRecognition();

    stopCurrentSpeechOutput();

    const newSessionId = createSessionId();
    sessionIdRef.current = newSessionId;
    setSessionIdForUser(username, newSessionId);

    setIsSpeaking(false);
    setIsBotTyping(false);
    setIsSettingsOpen(false);
    setInput('');
    setExpression(getExpressionByKey('smile'));
    setMessages([{ id: Date.now(), sender: 'bot', text: getWelcomeText(username) }]);
  };

  return (
    <div className={styles.homePageContainer}>
      <header className={styles.header}>
        <h1 className={styles.headerTitle}>
          {'TRANG CH\u1ee6 AIPA'} <Zap size={18} style={{ display: 'inline', color: 'var(--accent-strong)' }} />
        </h1>

        <div className={styles.headerActions}>
          <button type="button" className={styles.newChatButton} onClick={handleNewConversation}>
            <MessageSquarePlus size={16} />
            {'Tr\u00f2 chuy\u1ec7n m\u1edbi'}
          </button>
          <div style={{ position: 'relative' }}>
            <button className={styles.profileButton} onClick={() => setIsSettingsOpen(!isSettingsOpen)}>
              <Settings size={20} />
            </button>

            <SettingsPopover
              userData={userData}
              handleAction={handleSettingsAction}
              isSettingsOpen={isSettingsOpen}
              isAdmin={isAdmin}
            />
          </div>
        </div>
      </header>

      <div className={styles.mainContent}>
        <div className={styles.botArea}>
          <div className={styles.botImage}>
            <AnimeCompanion
              expression={expression}
              isSpeaking={isSpeaking}
              isRecording={isRecording}
              useImageModel={!hasModelImageError}
              onImageError={() => setHasModelImageError(true)}
            />
          </div>

          <div className={styles.botInfo}>
            <p className={styles.botName}>{'Tr\u1ee3 l\u00fd AI'}</p>
            <p className={styles.botStatus} style={{ color: !isVoiceMicEnabled ? 'var(--text-muted)' : isVoicePromptMode ? 'var(--danger-color)' : isSpeaking ? 'var(--accent-strong)' : 'var(--success-color)' }}>
              &#9679; {!isVoiceMicEnabled ? 'MIC \u0110ANG T\u1ea2T TRONG C\u00c0I \u0110\u1eb6T' : isVoicePromptMode ? '\u0110ANG NH\u1eacP GI\u1eccNG N\u00d3I' : isRecording ? 'MIC \u0110ANG CH\u1edc T\u1eea K\u00cdCH HO\u1ea0T' : isSpeaking ? '\u0110ANG \u0110\u1eccC C\u00c2U TR\u1ea2 L\u1edcI' : 'TR\u1ef0C TUY\u1ebeN - S\u1eb4N S\u00c0NG'}
            </p>
            <div className={styles.voiceSelector}>
              <button
                type="button"
                className={`${styles.voiceButton} ${isVoiceResponseEnabled ? styles.voiceButtonActive : ''}`}
                onClick={() => toggleVoiceResponse(!isVoiceResponseEnabled)}
                title={isVoiceResponseEnabled ? 'T\u1eaft gi\u1ecdng n\u00f3i ph\u1ea3n h\u1ed3i' : 'B\u1eadt gi\u1ecdng n\u00f3i ph\u1ea3n h\u1ed3i'}
              >
                {isVoiceResponseEnabled ? 'T\u1eaft \u0111\u1ecdc ph\u1ea3n h\u1ed3i' : 'B\u1eadt \u0111\u1ecdc ph\u1ea3n h\u1ed3i'}
              </button>
            </div>
            <p className="text-sm text-gray-500 mt-4">
              <Volume2 size={14} style={{ display: 'inline', marginRight: '6px' }} />
              {'T\u1ef1 \u0111\u1ed9ng \u0111\u1ecdc c\u00e2u tr\u1ea3 l\u1eddi, thay \u0111\u1ed5i bi\u1ec3u c\u1ea3m ng\u1eabu nhi\u00ean.'}
            </p>
            <div className={styles.tipsCard}>
              <button
                type="button"
                className={styles.tipsHeader}
                onClick={() => setIsTipsOpen((prev) => !prev)}
                aria-expanded={isTipsOpen}
              >
                <span className={styles.tipsTitle}>
                  <BookOpen size={14} />
                  {'Hướng dẫn sử dụng nhanh'}
                </span>
                <span className={styles.tipsToggle}>{isTipsOpen ? 'Ẩn' : 'Mở'}</span>
              </button>

              {isTipsOpen && (
                <ul className={styles.tipsList}>
                  {QUICK_TIPS.map((tip, index) => (
                    <li key={`tip-${index}`}>{tip}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>

        <div className={styles.chatArea} ref={chatAreaRef}>
          {messages.map((msg) => (
            <div key={msg.id} className={`${styles.messageBubble} ${msg.sender === 'user' ? styles.userMessage : styles.botMessage}`}>
              {msg.text}
            </div>
          ))}

          {isBotTyping && (
            <div className={styles.botMessage} style={{ maxWidth: '100px', padding: 0 }}>
              <LoadingDots />
            </div>
          )}
        </div>
      </div>

      <footer className={styles.footer}>
        <form onSubmit={handleSend} style={{ display: 'flex', width: '100%', gap: '10px' }}>
          <input
            type="text"
            placeholder={'Nh\u1eadp v\u0103n b\u1ea3n ho\u1eb7c n\u00f3i "kh\u1edfi \u0111\u1ed9ng nh\u1eadp gi\u1ecdng n\u00f3i" \u0111\u1ec3 b\u1eadt nh\u1eadp prompt b\u1eb1ng gi\u1ecdng n\u00f3i'}
            className={styles.chatInput}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                handleSend(e);
              }
            }}
            disabled={isBotTyping || isSavingControlCommand}
          />

          {input.trim() ? (
            <button type="submit" className={styles.sendButton} disabled={isBotTyping || isSavingControlCommand || !input.trim()}>
              <Send size={20} fill="white" />
            </button>
          ) : (
            <button
              type="button"
              className={`${styles.micButton} ${isRecording ? styles.active : ''}`}
              disabled
              title={isVoicePromptMode ? '\u0110ang nh\u1eadp gi\u1ecdng n\u00f3i' : 'Mic \u0111ang ch\u1edd t\u1eeb k\u00edch ho\u1ea1t'}
            >
              <Mic size={20} color="white" />
            </button>
          )}
        </form>
      </footer>
      <CommandGuideModal
        isOpen={isCommandGuideOpen}
        isLoading={isLoadingCommandGuide}
        error={commandGuideError}
        rules={commandGuideRules}
        sections={COMMAND_GUIDE_SECTIONS}
        onClose={closeCommandGuide}
      />
      <TrainModal
        isOpen={isTrainModalOpen}
        question={trainQuestion}
        answer={trainAnswer}
        isSubmitting={isSubmittingTrain}
        onQuestionChange={setTrainQuestion}
        onAnswerChange={setTrainAnswer}
        onClose={closeTrainModal}
        onSubmit={handleSubmitTrain}
      />
      <CommandSaveProgressModal
        isOpen={isSavingControlCommand}
        progress={saveControlCommandProgress}
        stageText={saveControlCommandStage}
      />
    </div>
  );
};

export default HomePage;



