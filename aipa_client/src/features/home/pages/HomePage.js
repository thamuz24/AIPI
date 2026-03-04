import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Settings, Lock, LogOut, Trash2, Send, Zap, Mic, Volume2, Shield, MessageSquarePlus } from 'lucide-react';
import styles from './HomePage.module.css';
import { useAuth } from '../../auth/context';
import { ANIME_MODEL_IMAGE_PATH } from '../model/animeModelConfig';
import { chatWithAssistantApi, trainAssistantApi } from '../../../shared/api';
import { appendPromptHistory, getUserSettings } from '../../../shared/services';

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
const randomExpression = () => EXPRESSIONS[Math.floor(Math.random() * EXPRESSIONS.length)];
const getWelcomeText = (username) => `Ch\u00e0o m\u1eebng tr\u1edf l\u1ea1i ${username}! T\u00f4i l\u00e0 tr\u1ee3 l\u00fd, b\u1ea1n c\u1ea7n h\u1ed7 tr\u1ee3 g\u00ec h\u00f4m nay?`;

const toChatHistory = (history) =>
  history.slice(-16).map((item) => ({
    sender: item.sender,
    text: item.text,
  }));

const estimateTokenCount = (value) => {
  const text = String(value || '').trim();
  if (!text) return 0;
  return Math.max(1, Math.round(text.length / 4));
};

const sanitizeDisplayText = (value) => {
  const text = String(value || '');
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

  text = sanitizeDisplayText(text);

  if (text.length > 1400) {
    text = `${text.slice(0, 1400).trimEnd()}...`;
  }
  return text;
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
  const [expression, setExpression] = useState(() => randomExpression());
  const [hasModelImageError, setHasModelImageError] = useState(false);
  const [userSettings, setUserSettings] = useState(() => getUserSettings(username));

  const chatAreaRef = useRef(null);
  const expressionTimerRef = useRef(null);
  const sessionIdRef = useRef(getOrCreateSessionId(username));
  const recognitionRef = useRef(null);
  const currentAudioRef = useRef(null);
  const audioObjectUrlRef = useRef('');

  const stopCurrentSpeechOutput = () => {
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
  };

  useEffect(() => {
    sessionIdRef.current = getOrCreateSessionId(username);
    setUserSettings(getUserSettings(username));
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
    if (userSettings.voiceChatEnabled) {
      return;
    }

    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setIsRecording(false);
    stopCurrentSpeechOutput();
  }, [userSettings.voiceChatEnabled]);

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
    expressionTimerRef.current = setInterval(() => {
      setExpression(randomExpression());
    }, 4000);

    return () => {
      if (expressionTimerRef.current) {
        clearInterval(expressionTimerRef.current);
      }
      if (recognitionRef.current) {
        recognitionRef.current.onresult = null;
        recognitionRef.current.onerror = null;
        recognitionRef.current.onend = null;
        recognitionRef.current.stop();
        recognitionRef.current = null;
      }
      stopCurrentSpeechOutput();
    };
  }, []);

  const playTextByVbee = async (text) => {
    if (!userSettings.voiceChatEnabled || !SHOULD_USE_VBEE_TTS || !text) {
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
        setExpression(randomExpression());
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
    if (!userSettings.voiceChatEnabled || !text) return;

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
      setExpression(randomExpression());
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
    try {
      const response = await chatWithAssistantApi({
        prompt: userPrompt,
        history: toChatHistory(historySnapshot),
        session_id: sessionIdRef.current,
      });
      answer = normalizeAnswerText(response?.answer || '');
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
    setExpression(randomExpression());
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

    if (userSettings.voiceChatEnabled) {
      const speechText = botResponse.text.length > 350 ? `${botResponse.text.slice(0, 350)}...` : botResponse.text;
      speakText(speechText);
    }
  };

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim() || isRecording) return;

    const messageText = input.trim();
    const newMessage = { id: Date.now(), sender: 'user', text: messageText };
    let historySnapshot = [];
    setMessages((prev) => {
      historySnapshot = [...prev, newMessage];
      return historySnapshot;
    });
    setInput('');
    handleBotResponse(messageText, historySnapshot, 'text');
  };

  const handleMicToggle = () => {
    if (isBotTyping) return;
    if (!userSettings.voiceChatEnabled) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          sender: 'bot',
          text: 'Trò chuyện giọng nói đang tắt. Vào Cài đặt để bật lại.',
        },
      ]);
      return;
    }

    if (!isRecording) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now() + 1,
            sender: 'bot',
            text: 'Tr\u00ecnh duy\u1ec7t hi\u1ec7n t\u1ea1i kh\u00f4ng h\u1ed7 tr\u1ee3 nh\u1eadn di\u1ec7n gi\u1ecdng n\u00f3i.',
          },
        ]);
        return;
      }

      const recognition = new SpeechRecognition();
      recognition.lang = 'vi-VN';
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      recognitionRef.current = recognition;
      setIsRecording(true);
      setExpression(randomExpression());

      recognition.onresult = (event) => {
        const transcript = Array.from(event.results || [])
          .map((result) => result?.[0]?.transcript || '')
          .join(' ')
          .trim();

        if (!transcript) {
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now() + 1,
              sender: 'bot',
              text: 'M\u00ecnh ch\u01b0a nghe r\u00f5 n\u1ed9i dung. B\u1ea1n th\u1eed n\u00f3i ch\u1eadm h\u01a1n nh\u00e9.',
            },
          ]);
          return;
        }

        const voiceMessage = { id: Date.now(), sender: 'user', text: `Gi\u1ecdng n\u00f3i: ${transcript}` };
        let historySnapshot = [];
        setMessages((prev) => {
          historySnapshot = [...prev, voiceMessage];
          return historySnapshot;
        });
        handleBotResponse(transcript, historySnapshot, 'voice');
      };

      recognition.onerror = (event) => {
        const message = event?.error === 'not-allowed'
          ? 'B\u1ea1n ch\u01b0a c\u1ea5p quy\u1ec1n micr\u00f4 cho tr\u00ecnh duy\u1ec7t.'
          : 'Kh\u00f4ng th\u1ec3 nh\u1eadn di\u1ec7n gi\u1ecdng n\u00f3i. B\u1ea1n th\u1eed l\u1ea1i.';

        setMessages((prev) => [
          ...prev,
          {
            id: Date.now() + 1,
            sender: 'bot',
            text: message,
          },
        ]);
      };

      recognition.onend = () => {
        setIsRecording(false);
        recognitionRef.current = null;
      };

      recognition.start();
    } else {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsRecording(false);
    }
  };

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

    if (action === 'admin') {
      navigate('/admin');
    }
  };

  const handleNewConversation = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }

    stopCurrentSpeechOutput();

    const newSessionId = createSessionId();
    sessionIdRef.current = newSessionId;
    setSessionIdForUser(username, newSessionId);

    setIsRecording(false);
    setIsSpeaking(false);
    setIsBotTyping(false);
    setIsSettingsOpen(false);
    setInput('');
    setExpression(randomExpression());
    setMessages([{ id: Date.now(), sender: 'bot', text: getWelcomeText(username) }]);
  };

  return (
    <div className={styles.homePageContainer}>
      <header className={styles.header}>
        <h1 className={styles.headerTitle}>
          {'TRANG CHỦ AIPA'} <Zap size={18} style={{ display: 'inline', color: '#00bcd4' }} />
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
            <p className={styles.botStatus} style={{ color: isRecording ? '#ef4444' : isSpeaking ? '#00bcd4' : '#48bb78' }}>
              &#9679; {!userSettings.voiceChatEnabled ? 'TRÒ CHUYỆN GIỌNG NÓI ĐÃ TẮT' : isRecording ? 'ĐANG GHI ÂM' : isSpeaking ? 'ĐANG ĐỌC CÂU TRẢ LỜI' : 'TRỰC TUYẾN - SẴN SÀNG'}
            </p>
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
            placeholder={userSettings.voiceChatEnabled ? 'Nhập văn bản hoặc dùng micrô...' : 'Nhập văn bản... (trò chuyện giọng nói đang tắt)'}
            className={styles.chatInput}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                handleSend(e);
              }
            }}
            disabled={isBotTyping || isRecording}
          />

          {input.trim() ? (
            <button type="submit" className={styles.sendButton} disabled={isBotTyping || isRecording}>
              <Send size={20} fill="white" />
            </button>
          ) : (
            <button
              type="button"
              className={`${styles.micButton} ${isRecording ? styles.active : ''}`}
              onClick={handleMicToggle}
              disabled={isBotTyping || !userSettings.voiceChatEnabled}
              title={userSettings.voiceChatEnabled ? 'Bật/tắt ghi âm' : 'Trò chuyện giọng nói đang tắt'}
            >
              <Mic size={20} color="white" />
            </button>
          )}
        </form>
      </footer>
    </div>
  );
};

export default HomePage;

