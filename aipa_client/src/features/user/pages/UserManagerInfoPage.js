import React, { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { User, Lock, Clock, Mail, Calendar, Key, Zap, Settings, Shield, Edit, Trash2 } from 'lucide-react';
import styles from './UserManagerInfoPage.module.css';
import { useAuth } from '../../auth/context';
import { updateProfileApi } from '../../../shared/api';
import {
  clearPromptHistory,
  getApiErrorMessage,
  getPromptHistory,
  getStoredAuth,
  getUserSettings,
  patchUserSettings,
  setStoredAuth,
} from '../../../shared/services';
import { useToast } from '../../../shared/ui';

function buildUserData(currentUser, role) {
  const username = currentUser?.username || 'TechUser_789';
  const email = currentUser?.email || 'user@ainode.com';
  const registrationTimestamp = Number(currentUser?.registrationTimestamp);
  const joinDate = Number.isFinite(registrationTimestamp) && registrationTimestamp > 0
    ? new Date(registrationTimestamp).toLocaleDateString()
    : 'Không có';

  return {
    username,
    email,
    joinDate,
    accessLevel: role === 'ROLE_ADMIN' ? 'Quản trị viên' : 'Người dùng Pro',
    lastLogin: new Date().toLocaleString(),
  };
}

function formatPromptDate(value) {
  const parsedDate = new Date(value);
  if (Number.isNaN(parsedDate.getTime())) {
    return 'Không có';
  }
  return parsedDate.toLocaleString();
}

function mapPrivacyLabel(value) {
  if (value === 'Private') return 'Riêng tư';
  if (value === 'Semi-Private') return 'Ẩn danh';
  if (value === 'Public') return 'Công khai';
  return 'Riêng tư';
}

function mapPromptStatusLabel(value) {
  if (value === 'Failed') return 'Thất bại';
  return 'Hoàn tất';
}

const UserManagerInfoPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { currentUser, auth, fetchMe } = useAuth();
  const { showToast } = useToast();
  const currentUsername = currentUser?.username || 'guest';

  const [activeTab, setActiveTab] = useState('account');
  const [isEditing, setIsEditing] = useState(false);
  const [isSavingProfile, setIsSavingProfile] = useState(false);

  const initialUserData = useMemo(() => buildUserData(currentUser, auth?.role), [currentUser, auth?.role]);
  const [userData, setUserData] = useState(initialUserData);
  const [userSettings, setUserSettings] = useState(() => getUserSettings(currentUsername));
  const [promptHistory, setPromptHistory] = useState(() => getPromptHistory(currentUsername));

  useEffect(() => {
    setUserData((prev) => {
      const next = buildUserData(currentUser, auth?.role);
      return {
        ...next,
        email: currentUser?.email || prev.email || next.email,
      };
    });
  }, [currentUser, auth?.role]);

  useEffect(() => {
    setUserSettings(getUserSettings(currentUsername));
    setPromptHistory(getPromptHistory(currentUsername));
  }, [currentUsername]);

  useEffect(() => {
    const queryTab = new URLSearchParams(location.search).get('tab');
    if (queryTab === 'account' || queryTab === 'security' || queryTab === 'history') {
      setActiveTab(queryTab);
    }
  }, [location.search]);

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    if (isSavingProfile) return;

    const nextUsername = String(userData.username || '').trim();
    const nextEmail = String(userData.email || '').trim();

    if (!nextUsername || !nextEmail) {
      showToast('Tên đăng nhập và email không được để trống.', { type: 'error' });
      return;
    }

    setIsSavingProfile(true);
    try {
      const response = await updateProfileApi({
        username: nextUsername,
        email: nextEmail,
      });

      const currentAuth = getStoredAuth();
      if (response?.accessToken && currentAuth?.refreshToken) {
        setStoredAuth({
          ...currentAuth,
          accessToken: response.accessToken,
          refreshToken: response?.refreshToken || currentAuth.refreshToken,
          tokenType: response?.tokenType || currentAuth?.tokenType || 'Bearer',
        });
      }

      setUserData((prev) => ({
        ...prev,
        username: response?.username || nextUsername,
        email: response?.email || nextEmail,
        lastLogin: new Date().toLocaleString(),
      }));

      await fetchMe();
      setIsEditing(false);
      showToast('Thông tin cá nhân đã được cập nhật và đồng bộ với máy chủ.', { type: 'success' });
    } catch (error) {
      showToast(getApiErrorMessage(error, 'Không cập nhật được thông tin cá nhân.'), { type: 'error' });
    } finally {
      setIsSavingProfile(false);
    }
  };

  const updateSettings = (patch, successMessage) => {
    const next = patchUserSettings(currentUsername, patch);
    setUserSettings(next);
    if (successMessage) {
      showToast(successMessage, { type: 'success' });
    }
  };

  const handlePrivacyChange = (e) => {
    const nextPrivacy = e.target.value;
    const autoShareData = nextPrivacy === 'Public';

    updateSettings(
      {
        privacySetting: nextPrivacy,
        shareDataForTraining: autoShareData ? true : userSettings.shareDataForTraining,
      },
      `Quyền riêng tư đã được đặt thành: ${mapPrivacyLabel(nextPrivacy)}`,
    );
  };

  const handleFaceVerificationToggle = () => {
    const nextValue = !userSettings.faceVerificationEnabled;
    const next = patchUserSettings(currentUsername, { faceVerificationEnabled: nextValue });
    patchUserSettings('guest', { faceVerificationEnabled: nextValue });
    setUserSettings(next);
    showToast(nextValue ? 'Đã bật xác nhận khuôn mặt.' : 'Đã tắt xác nhận khuôn mặt.', { type: 'success' });
  };

  const handleVoiceChatToggle = () => {
    const nextValue = !userSettings.voiceChatEnabled;
    const next = patchUserSettings(currentUsername, { voiceChatEnabled: nextValue });
    setUserSettings(next);
    showToast(nextValue ? 'Đã bật trò chuyện giọng nói và giọng đọc nữ hệ thống.' : 'Đã tắt trò chuyện giọng nói.', { type: 'success' });
  };

  const handleClearPromptHistory = () => {
    clearPromptHistory(currentUsername);
    setPromptHistory([]);
    showToast('Đã xóa toàn bộ lịch sử câu lệnh trên trình duyệt này.', { type: 'info' });
  };

  const handleRefreshPromptHistory = () => {
    setPromptHistory(getPromptHistory(currentUsername));
  };

  const renderAccountInfo = () => (
    <div className={styles.formSection}>
      <h2 className={styles.sectionTitle}>
        <User size={18} style={{ marginRight: '8px' }} /> Thông tin cơ bản
      </h2>

      {!isEditing ? (
        <div className={styles.infoGrid}>
          <div className={styles.infoCard}>
            <p>
              <strong><User size={14} style={{ marginRight: '5px' }} /> Tên đăng nhập:</strong> {userData.username}
            </p>
            <p>
              <strong><Mail size={14} style={{ marginRight: '5px' }} /> Email:</strong> {userData.email}
            </p>
            <p>
              <strong><Key size={14} style={{ marginRight: '5px' }} /> Cấp truy cập:</strong> {userData.accessLevel}
            </p>
          </div>
          <div className={styles.infoCard}>
            <p>
              <strong><Calendar size={14} style={{ marginRight: '5px' }} /> Ngày tham gia:</strong> {userData.joinDate}
            </p>
            <p>
              <strong><Clock size={14} style={{ marginRight: '5px' }} /> Đăng nhập cuối:</strong> {userData.lastLogin}
            </p>
            <p>
              <strong><Lock size={14} style={{ marginRight: '5px' }} /> Xác thực khuôn mặt:</strong> {userSettings.faceVerificationEnabled ? 'Đã bật' : 'Đã tắt'}
            </p>
            <p>
              <strong><Clock size={14} style={{ marginRight: '5px' }} /> Trò chuyện giọng nói:</strong> {userSettings.voiceChatEnabled ? 'Đã bật' : 'Đã tắt'}
            </p>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSaveProfile}>
          <div className={styles.inputGroup}>
            <label className={styles.inputLabel}>Tên đăng nhập</label>
            <input
              type="text"
              className={styles.inputField}
              value={userData.username}
              onChange={(e) => setUserData({ ...userData, username: e.target.value })}
            />
          </div>
          <div className={styles.inputGroup}>
            <label className={styles.inputLabel}>Email</label>
            <input
              type="email"
              className={styles.inputField}
              value={userData.email}
              onChange={(e) => setUserData({ ...userData, email: e.target.value })}
            />
          </div>
          <button type="submit" className={styles.saveButton} disabled={isSavingProfile}>
            <Zap size={16} style={{ marginRight: '8px' }} /> {isSavingProfile ? 'Đang lưu...' : 'Lưu thay đổi'}
          </button>
          <button type="button" className={styles.actionButton} style={{ backgroundColor: 'var(--text-muted)' }} onClick={() => setIsEditing(false)}>
            Hủy
          </button>
        </form>
      )}

      <button className={styles.actionButton} style={{ marginTop: '20px' }} onClick={() => setIsEditing(!isEditing)}>
        <Edit size={16} style={{ marginRight: '8px' }} /> {isEditing ? 'Hủy chỉnh sửa' : 'Chỉnh sửa thông tin'}
      </button>
    </div>
  );

  const renderSecurityPrivacy = () => (
    <>
      <div className={styles.formSection}>
        <h2 className={styles.sectionTitle}>
          <Shield size={18} style={{ marginRight: '8px' }} /> Bảo mật tài khoản
        </h2>
        <p className="text-sm text-gray-400 mb-4">Client lưu local và đồng bộ với backend ở các endpoint hỗ trợ.</p>

        <div className={styles.inputGroup}>
          <label className={styles.inputLabel}>Xác thực hai yếu tố (2FA)</label>
          <button
            type="button"
            className={styles.saveButton}
            style={{ backgroundColor: userSettings.twoFactorEnabled ? 'var(--danger-color)' : 'var(--success-color)', width: '220px' }}
            onClick={() =>
              updateSettings(
                { twoFactorEnabled: !userSettings.twoFactorEnabled },
                userSettings.twoFactorEnabled ? 'Đã tắt 2FA trên client.' : 'Đã bật 2FA trên client.',
              )}
          >
            {userSettings.twoFactorEnabled ? 'Tắt 2FA' : 'Kích hoạt 2FA'}
          </button>
        </div>

        <div className={styles.inputGroup}>
          <label className={styles.inputLabel}>Xác nhận khuôn mặt khi đăng nhập</label>
          <button
            type="button"
            className={styles.saveButton}
            style={{ backgroundColor: userSettings.faceVerificationEnabled ? 'var(--danger-color)' : 'var(--success-color)', width: '260px' }}
            onClick={handleFaceVerificationToggle}
          >
            {userSettings.faceVerificationEnabled ? 'Tắt xác nhận khuôn mặt' : 'Bật xác nhận khuôn mặt'}
          </button>
        </div>

        <div className={styles.inputGroup}>
          <label className={styles.inputLabel}>Trò chuyện giọng nói (mic + đọc câu trả lời)</label>
          <button
            type="button"
            className={styles.saveButton}
            style={{ backgroundColor: userSettings.voiceChatEnabled ? 'var(--danger-color)' : 'var(--success-color)', width: '280px' }}
            onClick={handleVoiceChatToggle}
          >
            {userSettings.voiceChatEnabled ? 'Tắt trò chuyện giọng nói' : 'Bật trò chuyện giọng nói'}
          </button>
        </div>
      </div>

      <div className={styles.formSection}>
        <h2 className={styles.sectionTitle}>
          <Lock size={18} style={{ marginRight: '8px' }} /> Quyền riêng tư dữ liệu
        </h2>
        <div className={styles.inputGroup}>
          <label className={styles.inputLabel}>Thiết lập quyền riêng tư tương tác</label>
          <select className={styles.selectField} value={userSettings.privacySetting} onChange={handlePrivacyChange}>
            <option value="Private">Riêng tư (Không dùng để đào tạo)</option>
            <option value="Semi-Private">Ẩn danh (Ẩn thông tin nhận dạng)</option>
            <option value="Public">Công khai (Đóng góp để cải tiến AI)</option>
          </select>
        </div>

        <div className={styles.inputGroup}>
          <label className={styles.inputLabel}>Chia sẻ dữ liệu để AI thông minh hơn</label>
          <button
            type="button"
            className={styles.saveButton}
            style={{ backgroundColor: userSettings.shareDataForTraining ? 'var(--danger-color)' : 'var(--success-color)', width: '320px' }}
            onClick={() =>
              updateSettings(
                { shareDataForTraining: !userSettings.shareDataForTraining },
                userSettings.shareDataForTraining
                  ? 'Đã tắt chia sẻ dữ liệu huấn luyện AI.'
                  : 'Đã bật chia sẻ dữ liệu huấn luyện AI.',
              )}
          >
            {userSettings.shareDataForTraining ? 'Tắt chia sẻ dữ liệu huấn luyện' : 'Bật chia sẻ dữ liệu huấn luyện'}
          </button>
        </div>

        <button type="button" className={`${styles.actionButton} ${styles.dangerButton}`} onClick={handleClearPromptHistory}>
          <Trash2 size={16} style={{ marginRight: '8px' }} /> Xóa toàn bộ lịch sử câu lệnh
        </button>
      </div>
    </>
  );

  const renderPromptHistory = () => (
    <div className={styles.formSection}>
      <h2 className={styles.sectionTitle}>
        <Clock size={18} style={{ marginRight: '8px' }} /> Lịch sử câu lệnh chat
      </h2>
      <p className="text-sm text-gray-400 mb-4">Dữ liệu được lưu local theo từng tài khoản đăng nhập trên client.</p>

      <div style={{ marginBottom: '10px' }}>
        <button type="button" className={styles.actionButton} onClick={handleRefreshPromptHistory}>
          Làm mới lịch sử
        </button>
      </div>

      <table className={styles.promptTable}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Loại câu lệnh</th>
            <th>Nội dung tóm tắt</th>
            <th>Ngày</th>
            <th>Trạng thái</th>
            <th>Token sử dụng</th>
          </tr>
        </thead>
        <tbody>
          {promptHistory.length === 0 && (
            <tr>
              <td colSpan={6}>Chưa có câu lệnh nào được lưu.</td>
            </tr>
          )}
          {promptHistory.map((prompt, index) => (
            <tr key={prompt.id}>
              <td>{index + 1}</td>
              <td>
                <span className={`${styles.statusTag} ${prompt.type === 'text' ? styles.text : styles.voice}`}>
                  {prompt.type === 'text' ? 'VĂN BẢN' : 'GIỌNG NÓI'}
                </span>
              </td>
              <td>{prompt.content.length > 70 ? `${prompt.content.substring(0, 70)}...` : prompt.content}</td>
              <td>{formatPromptDate(prompt.createdAt)}</td>
              <td>{mapPromptStatusLabel(prompt.status)}</td>
              <td>{prompt.tokens}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className={styles.container}>
      <div className={styles.contentBox}>
        <div className={styles.topActions}>
          <button type="button" className={styles.backButton} onClick={() => navigate('/home')}>
            Quay về trang chủ
          </button>
        </div>

        <h1 className={styles.title}>
          <Settings size={30} style={{ marginRight: '10px' }} /> Cài đặt và Quản lý tài khoản AI Node
        </h1>

        <div className={styles.tabsContainer}>
          <button className={`${styles.tabButton} ${activeTab === 'account' ? styles.tabButtonActive : ''}`} onClick={() => setActiveTab('account')}>
            <User size={16} style={{ marginRight: '8px' }} /> Thông tin cá nhân
          </button>
          <button className={`${styles.tabButton} ${activeTab === 'security' ? styles.tabButtonActive : ''}`} onClick={() => setActiveTab('security')}>
            <Shield size={16} style={{ marginRight: '8px' }} /> Bảo mật và Quyền riêng tư
          </button>
          <button className={`${styles.tabButton} ${activeTab === 'history' ? styles.tabButtonActive : ''}`} onClick={() => setActiveTab('history')}>
            <Clock size={16} style={{ marginRight: '8px' }} /> Lịch sử câu lệnh
          </button>
        </div>

        {activeTab === 'account' && renderAccountInfo()}
        {activeTab === 'security' && renderSecurityPrivacy()}
        {activeTab === 'history' && renderPromptHistory()}
      </div>
    </div>
  );
};

export default UserManagerInfoPage;
