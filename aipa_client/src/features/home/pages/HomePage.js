import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Settings, Lock, LogOut, Trash2, Send, Zap, Mic, Volume2, Shield, MessageSquarePlus } from 'lucide-react';
import styles from './HomePage.module.css';
import { useAuth } from '../../auth/context';
import { ANIME_MODEL_IMAGE_PATH } from '../model/animeModelConfig';
import { chatWithAssistantApi, trainAssistantApi } from '../../../shared/api';
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
  const hasMojibakeMarker = /[ÃÄÂâ€™â€œâ€\uFFFD]|á»|áº|Ä‘/u.test(text);
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

    const rawBad = (text.match(/[ÃÄÂâ€™â€œâ€\uFFFD]|á»|áº/gu) || []).length;
    const fixedBad = (decoded.match(/[ÃÄÂâ€™â€œâ€\uFFFD]|á»|áº/gu) || []).length;
    if (fixedBad < rawBad) {
      return decoded;
    }
  } catch (_error) {
    return text;
  }

  return text;
};
const sanitizeDisplayText = (value) => {
  const text = repairLikelyMojibake(value);
  const allowedPunct = new Set(['.', ',', '!', '?', ';', ':', "'", '"', '(', ')', '[', ']', '-', '/']);
  let output = '';

  for (const ch of text) {
    if (ch === '\n' || ch === '\r' || ch === '\t' || ch === ' ') {
      output += ch;
      continue;
    }
    if ((ch >= '0' && ch <= '9') || allowedPunct.has(ch)) {
      output += ch;
      continue;
    }
    if (/\p{Script=Latin}/u.test(ch) || /\p{Mark}/u.test(ch)) {
      output += ch;
    }
  }

  return output
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
              {'Hu\u0309y'}
            </button>
            <button type="submit" className={styles.trainPrimaryButton} disabled={isSubmitting || !question.trim() || !answer.trim()}>
              {isSubmitting ? 'Đang lưu...' : 'Lưu dữ liệu train'}
            </button>
          </div>
        </form>
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
  const [trainQuestion, setTrainQuestion] = useState('');
  const [trainAnswer, setTrainAnswer] = useState('');
  const [isSubmittingTrain, setIsSubmittingTrain] = useState(false);
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

    if (storedHistory.length > 0 && !requestFailed && userSettings.shareDataForTraining) {
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

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim() || isBotTyping) return;

    const messageText = input.trim();
    const normalizedMessage = normalizeVoiceCommand(messageText);
    const newMessage = { id: Date.now(), sender: 'user', text: messageText };

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

    let historySnapshot = [];
    setMessages((prev) => {
      historySnapshot = [...prev, newMessage];
      return historySnapshot;
    });
    setInput('');
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
  }, [isVoiceMicEnabled, isBotTyping, isSpeaking, pushBotMessage, stopVoiceRecognition, isVoicePromptMode, toggleVoiceResponse]);

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
      const sizeText = Number.isFinite(knowledgeSize) ? `${knowledgeSize}` : 'nhiều';
      pushBotMessage(`Đã lưu dữ liệu train thành công. Kho tri thức hiện có khoảng ${sizeText} mục.`);
    } catch (_error) {
      pushBotMessage('Không thể lưu dữ liệu train lúc này. Bạn thử lại sau.');
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
          {'TRANG CH\u1ee6 AIPA'} <Zap size={18} style={{ display: 'inline', color: '#00bcd4' }} />
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
            <p className={styles.botStatus} style={{ color: !isVoiceMicEnabled ? '#9ca3af' : isVoicePromptMode ? '#ef4444' : isSpeaking ? '#00bcd4' : '#48bb78' }}>
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
            disabled={isBotTyping}
          />

          {input.trim() ? (
            <button type="submit" className={styles.sendButton} disabled={isBotTyping || !input.trim()}>
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
    </div>
  );
};

export default HomePage;


