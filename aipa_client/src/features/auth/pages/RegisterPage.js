import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { User, Mail, Lock, Scan, CheckCircle, ArrowRight, ArrowLeft, Loader2, Eye, EyeOff } from 'lucide-react';
import styles from './RegisterPage.module.css';
import { useAuth } from '../context';
import { extractFaceEmbeddingApi } from '../../../shared/api';
import { getApiErrorMessage } from '../../../shared/services';

const AILogoEyes = () => {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const eyeRef = useRef(null);

  useEffect(() => {
    const handleMouseMove = (e) => {
      setMousePosition({ x: e.clientX, y: e.clientY });
    };

    window.addEventListener('mousemove', handleMouseMove);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, []);

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
      <div className={styles.aiLogoOuter}>
        <div className={styles.eye}>
          <div className={styles.pupil} style={getRotationStyle(eyeRef.current?.children[0]?.children[0])}></div>
        </div>
        <div className={styles.eye}>
          <div className={styles.pupil} style={getRotationStyle(eyeRef.current?.children[0]?.children[1])}></div>
        </div>
      </div>
    </div>
  );
};

const RegisterPage = () => {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [isLoading, setIsLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    faceEmbeddingsJson: '',
  });
  const [fieldErrors, setFieldErrors] = useState({ username: '', email: '', password: '' });
  const [formError, setFormError] = useState('');
  const [formInfo, setFormInfo] = useState('');
  const [isCameraReady, setIsCameraReady] = useState(false);
  const [isCameraUnavailable, setIsCameraUnavailable] = useState(false);
  const [isFaceScanSkipped, setIsFaceScanSkipped] = useState(false);
  const videoRef = useRef(null);
  const mediaStreamRef = useRef(null);

  const isNoCameraError = (error) => {
    const code = String(error?.name || '').toLowerCase();
    const message = String(error?.message || '').toLowerCase();

    return code === 'notfounderror' || code === 'overconstrainederror' || message.includes('không tìm thấy camera') || message.includes('khong tim thay camera');
  };

  const createSkippedFaceEmbeddings = () =>
    JSON.stringify({
      vector: Array.from({ length: 128 }, () => 0),
      dimension: 128,
      skipped: true,
      reason: 'camera_not_found',
      timestamp: new Date().toISOString(),
    });

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

  const validateStepOne = () => {
    const nextErrors = { username: '', email: '', password: '' };
    const username = formData.username.trim();
    const email = formData.email.trim();
    const password = formData.password;

    if (!username) {
      nextErrors.username = 'Vui lòng nhập tên đăng nhập.';
    } else if (username.length < 3) {
      nextErrors.username = 'Tên đăng nhập tối thiểu 3 ký tự.';
    }

    if (!email) {
      nextErrors.email = 'Vui lòng nhập email.';
    } else if (!/^\S+@\S+\.\S+$/.test(email)) {
      nextErrors.email = 'Email không hợp lệ.';
    }

    if (!password) {
      nextErrors.password = 'Vui lòng nhập mật khẩu.';
    } else if (password.length < 6) {
      nextErrors.password = 'Mật khẩu tối thiểu 6 ký tự.';
    }

    setFieldErrors(nextErrors);
    return !nextErrors.username && !nextErrors.email && !nextErrors.password;
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
          const sourceError = secondError || firstError;
          const mappedError = new Error(mapCameraErrorMessage(sourceError));
          mappedError.name = sourceError?.name || 'CameraError';
          throw mappedError;
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

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setFieldErrors((prev) => ({ ...prev, [name]: '' }));
    setFormError('');
  };

  const handleNextStep = (e) => {
    e.preventDefault();
    if (currentStep !== 1) return;

    setFormInfo('');
    setFormError('');

    if (!validateStepOne()) {
      return;
    }
    setCurrentStep(2);
  };

  const handleFaceScan = async () => {
    setFormError('');
    setFormInfo('');
    setIsFaceScanSkipped(false);
    setIsLoading(true);

    try {
      await startCamera();
      await new Promise((resolve) => setTimeout(resolve, 450));

      const image = captureFrameAsBase64();
      const response = await extractFaceEmbeddingApi({ image });
      const embedding = Array.isArray(response?.embedding) ? response.embedding : [];

      if (!embedding.length) {
        throw new Error('Không tìm thấy khuôn mặt trong khung hình.');
      }

      const capturedEmbeddings = JSON.stringify({
        vector: embedding,
        dimension: embedding.length,
        timestamp: new Date().toISOString(),
      });

      setIsCameraUnavailable(false);
      setFormData((prev) => ({ ...prev, faceEmbeddingsJson: capturedEmbeddings }));
      setFormInfo('Quét khuôn mặt thành công. Bạn có thể hoàn tất đăng ký.');
    } catch (error) {
      if (isNoCameraError(error)) {
        setIsCameraUnavailable(true);
        setFormInfo('Không tìm thấy camera. Bạn có thể bỏ qua bước quét khuôn mặt để tiếp tục đăng ký.');
      }
      setFormError(getApiErrorMessage(error, 'Không thể quét khuôn mặt. Kiểm tra camera và thử lại.'));
    } finally {
      stopCamera();
      setIsLoading(false);
    }
  };

  const handleSkipFaceScan = () => {
    setFormError('');
    setIsFaceScanSkipped(true);
    setFormData((prev) => ({ ...prev, faceEmbeddingsJson: prev.faceEmbeddingsJson || createSkippedFaceEmbeddings() }));
    setFormInfo('Bạn đã bỏ qua bước quét khuôn mặt vì không tìm thấy camera.');
  };

  const handleFinalSubmit = async (e) => {
    if (e?.preventDefault) e.preventDefault();

    setFormError('');

    if (!validateStepOne()) {
      setCurrentStep(1);
      return;
    }

    const isFaceStepComplete = Boolean(formData.faceEmbeddingsJson) || (isCameraUnavailable && isFaceScanSkipped);

    if (!isFaceStepComplete) {
      setFormError('Vui lòng hoàn thành bước quét khuôn mặt. Nếu thiết bị không có camera, hãy bấm "Bỏ qua quét khuôn mặt".');
      return;
    }

    if (isLoading) return;

    setIsLoading(true);
    try {
      const registerPayload = {
        username: formData.username.trim(),
        email: formData.email.trim(),
        password: formData.password,
      };

      if (formData.faceEmbeddingsJson) {
        registerPayload.faceEmbeddingsJson = formData.faceEmbeddingsJson;
      } else if (isCameraUnavailable && isFaceScanSkipped) {
        registerPayload.faceEmbeddingsJson = createSkippedFaceEmbeddings();
      }

      await register(registerPayload);
      navigate('/home', { replace: true });
    } catch (error) {
      setFormError(getApiErrorMessage(error, 'Đăng ký thất bại.'));
    } finally {
      setIsLoading(false);
    }
  };

  const isStep1Complete = formData.username.trim() && formData.email.trim() && formData.password.length >= 6;
  const isFaceStepComplete = Boolean(formData.faceEmbeddingsJson) || (isCameraUnavailable && isFaceScanSkipped);

  return (
    <div className={styles.loginPageContainer}>
      <div className={styles.loginBox}>
        <div className={styles.aiGlow}></div>

        <div className={styles.loginContent}>
          <div className={styles.header}>
            <AILogoEyes />
            <h1 className={styles.title}>ĐĂNG KÝ AI NODE</h1>
            <p className="text-sm text-gray-400 mt-1">Tạo tài khoản cho hệ thống AI.</p>
          </div>

          <div className={styles.stepContainer}>
            <div className={styles.stepItem}>
              <div className={`${styles.stepCircle} ${currentStep >= 1 ? styles.stepCircleActive : ''}`}>1</div>
              <span className={styles.stepLabel}>Thông tin cơ bản</span>
              <div className={styles.stepLine}></div>
            </div>

            <div className={styles.stepItem}>
              <div className={`${styles.stepCircle} ${currentStep === 2 ? styles.stepCircleActive : ''} ${isFaceStepComplete ? styles.stepCircleCompleted : ''}`}>
                {isFaceStepComplete ? <CheckCircle size={16} /> : 2}
              </div>
              <span className={styles.stepLabel}>Xác thực khuôn mặt</span>
            </div>
          </div>

          <form onSubmit={currentStep === 1 ? handleNextStep : handleFinalSubmit}>
            {formError && <div className={styles.errorMessage}>{formError}</div>}
            {formInfo && <div className={styles.infoMessage}>{formInfo}</div>}

            {currentStep === 1 && (
              <>
                <div className={styles.requirementBox}>
                  <p className={styles.requirementTitle}>Yêu cầu tạo tài khoản</p>
                  <ul className={styles.requirementList}>
                    <li>Tên đăng nhập: tối thiểu 3 ký tự, không chứa khoảng trắng đầu/cuối.</li>
                    <li>Mật khẩu: tối thiểu 6 ký tự.</li>
                  </ul>
                </div>
                <div className={styles.inputGroup}>
                  <label htmlFor="username" className={styles.inputLabel}>
                    <User size={16} style={{ marginRight: '8px', color: 'var(--accent-strong)' }} />
                    Tên đăng nhập
                  </label>
                  <input
                    id="username"
                    name="username"
                    type="text"
                    placeholder="Chọn ID người dùng"
                    className={`${styles.inputField} ${fieldErrors.username ? styles.inputFieldError : ''}`}
                    value={formData.username}
                    onChange={handleInputChange}
                  />
                  {fieldErrors.username && <p className={styles.fieldErrorText}>{fieldErrors.username}</p>}
                </div>
                <div className={styles.inputGroup}>
                  <label htmlFor="email" className={styles.inputLabel}>
                    <Mail size={16} style={{ marginRight: '8px', color: 'var(--accent-strong)' }} />
                    Email
                  </label>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    placeholder="Nhập email để xác thực"
                    className={`${styles.inputField} ${fieldErrors.email ? styles.inputFieldError : ''}`}
                    value={formData.email}
                    onChange={handleInputChange}
                  />
                  {fieldErrors.email && <p className={styles.fieldErrorText}>{fieldErrors.email}</p>}
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
                      placeholder="Tạo mật khẩu an toàn"
                      className={`${styles.inputField} ${fieldErrors.password ? styles.inputFieldError : ''}`}
                      value={formData.password}
                      onChange={handleInputChange}
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

                <button type="submit" disabled={!isStep1Complete} className={styles.loginButton}>
                  Tiếp theo: Quét khuôn mặt <ArrowRight size={18} style={{ marginLeft: '8px' }} />
                </button>
              </>
            )}

            {currentStep === 2 && (
              <>
                <div className={styles.faceScanArea} style={{ minHeight: '180px' }}>
                  <video
                    ref={videoRef}
                    autoPlay
                    muted
                    playsInline
                    style={{
                      width: '100%',
                      maxWidth: '340px',
                      borderRadius: '12px',
                      marginBottom: '12px',
                      display: isLoading && !formData.faceEmbeddingsJson && isCameraReady ? 'block' : 'none',
                    }}
                  />
                  <Scan className={`${styles.scanIcon} ${isLoading ? styles.scanning : ''}`} style={{ color: isFaceStepComplete ? 'var(--success-color)' : 'var(--accent-strong)' }} size={64} />
                  <p className="text-lg font-medium text-white">
                    {isLoading
                      ? 'Đang phân tích khuôn mặt...'
                      : isFaceScanSkipped
                        ? 'Đã bỏ qua bước quét khuôn mặt.'
                        : isFaceStepComplete
                        ? 'Đã quét xong. Dữ liệu sẵn sàng.'
                        : 'Nhấn nút bên dưới để bắt đầu quét.'}
                  </p>
                </div>

                <div style={{ display: 'flex', gap: '10px' }}>
                  <button type="button" onClick={() => setCurrentStep(1)} className={styles.loginButton} style={{ background: 'var(--text-muted)', flex: 1 }}>
                    <ArrowLeft size={18} style={{ marginRight: '8px' }} /> Quay lại
                  </button>

                  {isCameraUnavailable && !isFaceStepComplete && (
                    <button type="button" onClick={handleSkipFaceScan} disabled={isLoading} className={styles.loginButton} style={{ background: 'var(--warning-color)', flex: 2 }}>
                      BỎ QUA QUÉT KHUÔN MẶT
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={isFaceStepComplete ? handleFinalSubmit : handleFaceScan}
                    disabled={isLoading}
                    className={styles.loginButton}
                    style={{ background: isFaceStepComplete ? 'var(--success-color)' : 'var(--accent-hover)', flex: 2 }}
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className={styles.loadingIcon} /> Đang xử lý...
                      </>
                    ) : isFaceStepComplete ? (
                      <>
                        HOÀN TẤT ĐĂNG KÝ <CheckCircle size={18} style={{ marginLeft: '8px' }} />
                      </>
                    ) : (
                      <>KHỞI TẠO QUÉT KHUÔN MẶT</>
                    )}
                  </button>
                </div>
              </>
            )}
          </form>

          <div className={styles.footerText}>
            <p>
              Đã có tài khoản{' '}
              <Link to="/" className={styles.highlight}>
                Đăng nhập ngay
              </Link>
            </p>
            <p>
              <span className={styles.highlight}>Bảo mật:</span> Dữ liệu khuôn mặt chỉ dùng cho mục đích xác thực.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
