import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { User, Lock, Scan, Loader2, KeyRound, Eye, EyeOff } from 'lucide-react';
import styles from './LoginPage.module.css';
import { useAuth } from '../context';
import { extractFaceEmbeddingApi } from '../../../shared/api';
import { getApiErrorMessage, getUserSettings } from '../../../shared/services';

const AILogoEyes = ({ isPasswordFocused }) => {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const eyeRef = useRef(null);

  useEffect(() => {
    if (isPasswordFocused) return;

    const handleMouseMove = (e) => {
      setMousePosition({ x: e.clientX, y: e.clientY });
    };

    window.addEventListener('mousemove', handleMouseMove);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, [isPasswordFocused]);

  const getRotationStyle = (eyeElement) => {
    if (!eyeElement || !eyeRef.current) return {};

    const eyeRect = eyeElement.getBoundingClientRect();
    const eyeCenterX = eyeRect.left + eyeRect.width / 2;
    const eyeCenterY = eyeRect.top + eyeRect.height / 2;

    const deltaX = mousePosition.x - eyeCenterX;
    const deltaY = mousePosition.y - eyeCenterY;
    const angleRad = Math.atan2(deltaY, deltaX);

    const maxMove = 3;
    const xMove = maxMove * Math.cos(angleRad);
    const yMove = maxMove * Math.sin(angleRad);

    return {
      transform: `translate(-50%, -50%) translate(${xMove}px, ${yMove}px)`,
    };
  };

  return (
    <div className={styles.aiLogoContainer} ref={eyeRef}>
      <div className={`${styles.logoHand} ${styles.left} ${isPasswordFocused ? styles.active : ''}`}></div>

      <div className={styles.aiLogoOuter}>
        <div className={styles.eye} style={{ opacity: isPasswordFocused ? 0 : 1 }}>
          <div className={styles.pupil} style={getRotationStyle(eyeRef.current?.children[1]?.children[0])}></div>
        </div>
        <div className={styles.eye} style={{ opacity: isPasswordFocused ? 0 : 1 }}>
          <div className={styles.pupil} style={getRotationStyle(eyeRef.current?.children[1]?.children[1])}></div>
        </div>
      </div>

      <div className={`${styles.logoHand} ${styles.right} ${isPasswordFocused ? styles.active : ''}`}></div>
    </div>
  );
};

const LoginPage = () => {
  const navigate = useNavigate();
  const { login, loginByFace } = useAuth();

  const [isLoading, setIsLoading] = useState(false);
  const [loginMode, setLoginMode] = useState('credentials');
  const [isPasswordFocused, setIsPasswordFocused] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({ username: '', password: '' });
  const [fieldErrors, setFieldErrors] = useState({ username: '', password: '' });
  const [formError, setFormError] = useState('');
  const [formInfo, setFormInfo] = useState('');
  const [isCameraReady, setIsCameraReady] = useState(false);
  const isFaceVerificationEnabled = getUserSettings('guest').faceVerificationEnabled;
  const videoRef = useRef(null);
  const mediaStreamRef = useRef(null);

  const mapLoginErrorMessage = (error) => {
    const status = Number(error?.response?.status || 0);
    const rawMessage = String(error?.response?.data?.message || error?.message || '').toLowerCase();

    if (!formData.username.trim() || !formData.password) {
      return 'Vui lòng nhập đầy đủ tài khoản và mật khẩu.';
    }

    if (
      status === 404 ||
      rawMessage.includes('not found') ||
      rawMessage.includes('không tồn tại') ||
      rawMessage.includes('khong ton tai') ||
      rawMessage.includes('user not found')
    ) {
      return 'Tài khoản chưa tồn tại.';
    }

    if (
      status === 401 ||
      rawMessage.includes('invalid') ||
      rawMessage.includes('unauthorized') ||
      rawMessage.includes('sai mật khẩu') ||
      rawMessage.includes('sai mat khau') ||
      rawMessage.includes('wrong password') ||
      rawMessage.includes('bad credentials') ||
      rawMessage.includes('thông tin đăng nhập không hợp lệ') ||
      rawMessage.includes('thong tin dang nhap khong hop le')
    ) {
      return 'Tài khoản hoặc mật khẩu không đúng.';
    }

    return getApiErrorMessage(error, 'Đăng nhập thất bại. Vui lòng thử lại.');
  };

  const mapCameraErrorMessage = (error) => {
    const code = String(error?.name || '').toLowerCase();
    if (code === 'notallowederror' || code === 'securityerror') {
      return 'Bạn đang chặn quyền camera. Hãy cấp quyền camera cho trình duyệt.';
    }
    if (code === 'notfounderror' || code === 'overconstrainederror') {
      return 'Không tìm thấy camera phù hợp. Hãy kiểm tra webcam và thử lại.';
    }
    if (code === 'notreadableerror') {
      return 'Camera đang được ứng dụng khác sử dụng. Hãy tắt ứng dụng đó rồi thử lại.';
    }
    return 'Không thể khởi động camera. Vui lòng kiểm tra thiết bị và thử lại.';
  };

  const stopCamera = () => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setIsCameraReady(false);
  };

  const startCamera = async () => {
    if (!navigator?.mediaDevices?.getUserMedia) {
      throw new Error('Trình duyệt không hỗ trợ camera.');
    }

    if (!mediaStreamRef.current) {
      try {
        mediaStreamRef.current = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: 'user' } },
          audio: false,
        });
      } catch (firstError) {
        try {
          mediaStreamRef.current = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: false,
          });
        } catch (secondError) {
          throw new Error(mapCameraErrorMessage(secondError || firstError));
        }
      }
    }

    if (videoRef.current) {
      videoRef.current.srcObject = mediaStreamRef.current;
      await videoRef.current.play();
    }

    setIsCameraReady(true);
  };

  const captureFrameAsBase64 = () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth || !video.videoHeight) {
      throw new Error('Camera chưa sẵn sàng, vui lòng thử lại.');
    }

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext('2d');

    if (!context) {
      throw new Error('Không tạo được bộ đệm ảnh.');
    }

    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.92);
  };

  useEffect(() => () => stopCamera(), []);

  const validateCredentialsForm = () => {
    const username = formData.username.trim();
    const password = formData.password;
    const nextFieldErrors = { username: '', password: '' };

    if (!username) {
      nextFieldErrors.username = 'Vui lòng nhập tên đăng nhập hoặc email.';
    }
    if (!password) {
      nextFieldErrors.password = 'Vui lòng nhập mật khẩu.';
    }

    setFieldErrors(nextFieldErrors);
    if (nextFieldErrors.username || nextFieldErrors.password) {
      setFormError('Vui lòng nhập đầy đủ thông tin đăng nhập.');
    }
    return !nextFieldErrors.username && !nextFieldErrors.password;
  };

  const handleFaceLogin = async () => {
    if (!isFaceVerificationEnabled) {
      setFormError('Xác nhận khuôn mặt đang được tắt trên client.');
      return;
    }

    setIsLoading(true);
    setFormError('');
    setFormInfo('');

    try {
      await startCamera();
      setFormInfo('Đang quét khuôn mặt...');
      await new Promise((resolve) => setTimeout(resolve, 450));

      const image = captureFrameAsBase64();
      const response = await extractFaceEmbeddingApi({ image });
      const embedding = Array.isArray(response?.embedding) ? response.embedding : [];

      if (!embedding.length) {
        throw new Error('Không tìm thấy khuôn mặt trong khung hình.');
      }

      const faceEmbeddingsJson = JSON.stringify({
        vector: embedding,
        dimension: embedding.length,
        timestamp: new Date().toISOString(),
      });

      const session = await loginByFace({ faceEmbeddingsJson });
      navigate(session?.role === 'ROLE_ADMIN' ? '/admin' : '/home', { replace: true });
    } catch (error) {
      setFormError(getApiErrorMessage(error, 'Đăng nhập khuôn mặt thất bại.'));
    } finally {
      stopCamera();
      setFormInfo('');
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isLoading) return;

    setFormError('');
    setFormInfo('');

    if (loginMode === 'face') {
      await handleFaceLogin();
      return;
    }

    if (!validateCredentialsForm()) {
      return;
    }

    setIsLoading(true);
    try {
      const session = await login({
        usernameOrEmail: formData.username.trim(),
        password: formData.password,
      });
      navigate(session?.role === 'ROLE_ADMIN' ? '/admin' : '/home', { replace: true });
    } catch (error) {
      setFormError(mapLoginErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    setFormError('');
    setFormInfo('');
    setShowPassword(false);
    if (loginMode !== 'face') {
      stopCamera();
    }
  }, [loginMode]);

  return (
    <div className={styles.loginPageContainer}>
      <div className={styles.loginBox}>
        <div className={styles.aiGlow}></div>

        <div className={styles.loginContent}>
          <div className={styles.header}>
            <AILogoEyes isPasswordFocused={isPasswordFocused} />
            <h1 className={styles.title}>ĐĂNG NHẬP AI</h1>
            <p className="text-sm text-gray-400 mt-1">Chọn phương thức xác thực.</p>
          </div>

          <div className={styles.tabsContainer}>
            <button
              onClick={() => setLoginMode('credentials')}
              className={`${styles.tabButton} ${loginMode === 'credentials' ? styles.tabButtonActive : ''}`}
            >
              <KeyRound size={16} style={{ display: 'inline', marginRight: '8px' }} />
              Tài khoản và mật khẩu
            </button>
            <button
              onClick={() => {
                if (!isFaceVerificationEnabled) {
                  setLoginMode('credentials');
                  setFormInfo('Xác nhận khuôn mặt đang được tắt trên client.');
                  return;
                }
                setLoginMode('face');
              }}
              className={`${styles.tabButton} ${loginMode === 'face' ? styles.tabButtonActive : ''}`}
              disabled={!isFaceVerificationEnabled}
              style={!isFaceVerificationEnabled ? { opacity: 0.45, cursor: 'not-allowed' } : undefined}
            >
              <Scan size={16} style={{ display: 'inline', marginRight: '8px' }} />
              Nhận dạng khuôn mặt
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            {formError && <div className={styles.errorMessage}>{formError}</div>}
            {formInfo && <div className={styles.infoMessage}>{formInfo}</div>}

            {loginMode === 'credentials' && (
              <>
                <div className={styles.inputGroup}>
                  <label htmlFor="username" className={styles.inputLabel}>
                    <User size={16} style={{ marginRight: '8px', color: 'var(--accent-strong)' }} />
                    Tên đăng nhập
                  </label>
                  <input
                    id="username"
                    name="username"
                    type="text"
                    placeholder="Nhập tài khoản hoặc email"
                    className={`${styles.inputField} ${fieldErrors.username ? styles.inputFieldError : ''}`}
                    value={formData.username}
                    onChange={(event) => {
                      setFormData((prev) => ({ ...prev, username: event.target.value }));
                      setFieldErrors((prev) => ({ ...prev, username: '' }));
                      setFormError('');
                    }}
                  />
                  {fieldErrors.username && <p className={styles.fieldErrorText}>{fieldErrors.username}</p>}
                </div>
                <div className={styles.inputGroup}>
                  <label htmlFor="password" className={styles.inputLabel}>
                    <Lock size={16} style={{ marginRight: '8px', color: 'var(--accent-strong)' }} />
                    Mật khẩu
                  </label>
                  <div className={styles.passwordFieldWrap}>
                    <input
                      id="password"
                      name="password"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Nhập mật khẩu"
                      className={`${styles.inputField} ${fieldErrors.password ? styles.inputFieldError : ''}`}
                      value={formData.password}
                      onChange={(event) => {
                        setFormData((prev) => ({ ...prev, password: event.target.value }));
                        setFieldErrors((prev) => ({ ...prev, password: '' }));
                        setFormError('');
                      }}
                      onFocus={() => setIsPasswordFocused(true)}
                      onBlur={() => setIsPasswordFocused(false)}
                    />
                    <button
                      type="button"
                      className={styles.visibilityButton}
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => setShowPassword((prev) => !prev)}
                      aria-label={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  {fieldErrors.password && <p className={styles.fieldErrorText}>{fieldErrors.password}</p>}
                </div>
              </>
            )}

            {loginMode === 'face' && (
              <div className={styles.faceScanArea}>
                <video
                  ref={videoRef}
                  autoPlay
                  muted
                  playsInline
                  style={{
                    width: '100%',
                    maxWidth: '320px',
                    borderRadius: '12px',
                    margin: '0 auto 12px',
                    display: isLoading && isCameraReady ? 'block' : 'none',
                  }}
                />
                <Scan className={`${styles.scanIcon} ${isLoading ? styles.scanning : ''}`} style={{ color: isLoading ? 'var(--success-color)' : 'var(--accent-strong)' }} size={64} />
                <p className="text-lg font-medium text-white">
                  {isLoading ? 'Đang quét và xác thực khuôn mặt...' : 'Vui lòng nhìn vào camera để xác thực.'}
                </p>
                <p className="text-sm text-gray-500 mt-1">Hệ thống sẽ chụp 1 khung hình để đối chiếu khuôn mặt.</p>
              </div>
            )}

            <button type="submit" disabled={isLoading} className={styles.loginButton}>
              {isLoading ? (
                <>
                  <Loader2 className={styles.loadingIcon} />
                  {loginMode === 'credentials' ? 'Đang xác thực thông tin...' : 'Đang quét khuôn mặt...'}
                </>
              ) : (
                loginMode === 'credentials' ? 'Đăng nhập hệ thống AI' : 'Đăng nhập bằng khuôn mặt'
              )}
            </button>
          </form>

          <div className={styles.footerText}>
            <p>
              Chưa có tài khoản{' '}
              <Link to="/register" className={styles.highlight}>
                Đăng ký ngay
              </Link>
            </p>
            <p>
              <span className={styles.highlight}>Cảnh báo:</span> Mọi truy cập đều được giám sát bởi hệ thống phân quyền.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
