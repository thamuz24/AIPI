import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Ban, Clock3, RefreshCw, Shield, Users } from 'lucide-react';
import styles from './AdminDashboardPage.module.css';
import { banUserApi, fetchAdminBanLogsApi, fetchAdminUsersApi } from '../../../shared/api';
import { getApiErrorMessage } from '../../../shared/services';

function formatTime(timestamp) {
  if (!timestamp) return 'Không có';
  return new Date(timestamp).toLocaleString('vi-VN');
}

function getRoleLabel(role) {
  if (role === 1 || role === 'ROLE_ADMIN') return 'Quản trị viên';
  return 'Người dùng';
}

const AdminDashboardPage = ({ initialTab = 'users' }) => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(initialTab);
  const [users, setUsers] = useState([]);
  const [logs, setLogs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const historySummary = useMemo(() => {
    const uniqueUsers = new Set(logs.map((item) => item.userId));
    const uniqueAdmins = new Set(logs.map((item) => item.bannedBy).filter(Boolean));

    return {
      totalActions: logs.length,
      totalUsersAffected: uniqueUsers.size,
      totalAdmins: uniqueAdmins.size,
      latestActionAt: logs[0]?.bannedAt || null,
    };
  }, [logs]);

  const fetchData = useCallback(async ({ silent = false } = {}) => {
    if (silent) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError('');

    try {
      const [usersResponse, logsResponse] = await Promise.all([
        fetchAdminUsersApi(),
        fetchAdminBanLogsApi(),
      ]);
      setUsers(Array.isArray(usersResponse) ? usersResponse : []);
      setLogs(Array.isArray(logsResponse) ? logsResponse : []);
    } catch (apiError) {
      setError(getApiErrorMessage(apiError, 'Không tải được dữ liệu quản trị.'));
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  const handleBanUser = async (user) => {
    const reason = window.prompt(`Nhập lý do khóa tài khoản "${user.username}" (tối thiểu 5 ký tự):`, '');
    if (reason === null) {
      return;
    }

    const trimmedReason = reason.trim();
    if (trimmedReason.length < 5) {
      setError('Lý do khóa tài khoản phải có tối thiểu 5 ký tự.');
      return;
    }

    setIsSubmitting(true);
    setError('');
    try {
      await banUserApi(user.id, { reason: trimmedReason });
      await fetchData({ silent: true });
    } catch (apiError) {
      setError(getApiErrorMessage(apiError, 'Không khóa được tài khoản.'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderUsersTable = () => (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Tên đăng nhập</th>
            <th>Email</th>
            <th>Vai trò</th>
            <th>Trạng thái</th>
            <th>Ngày tạo</th>
            <th>Hành động</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => {
            const isAdmin = user.role === 1 || user.role === 'ROLE_ADMIN';
            const isActive = Boolean(user.active);
            return (
              <tr key={user.id}>
                <td>{user.id}</td>
                <td>{user.username}</td>
                <td>{user.email}</td>
                <td>
                  <span className={`${styles.badge} ${isAdmin ? styles.badgeAdmin : styles.badgeUser}`}>
                    {getRoleLabel(user.role)}
                  </span>
                </td>
                <td>
                  <span className={`${styles.badge} ${isActive ? styles.badgeActive : styles.badgeBanned}`}>
                    {isActive ? 'Đang hoạt động' : 'Đã khóa'}
                  </span>
                </td>
                <td>{formatTime(user.registrationTimestamp)}</td>
                <td>
                  <button
                    type="button"
                    className={styles.banButton}
                    disabled={isSubmitting || isAdmin || !isActive}
                    onClick={() => handleBanUser(user)}
                  >
                    <Ban size={14} />
                    Khóa
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {!users.length && <div className={styles.empty}>Chưa có tài khoản nào.</div>}
    </div>
  );

  const renderHistory = () => (
    <>
      <div className={styles.summaryGrid}>
        <div className={styles.summaryCard}>
          <span>Tổng hành vi</span>
          <strong>{historySummary.totalActions}</strong>
        </div>
        <div className={styles.summaryCard}>
          <span>Tài khoản bị tác động</span>
          <strong>{historySummary.totalUsersAffected}</strong>
        </div>
        <div className={styles.summaryCard}>
          <span>Quản trị viên đã thao tác</span>
          <strong>{historySummary.totalAdmins}</strong>
        </div>
        <div className={styles.summaryCard}>
          <span>Lần gần nhất</span>
          <strong>{formatTime(historySummary.latestActionAt)}</strong>
        </div>
      </div>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Mã nhật ký</th>
              <th>Tài khoản</th>
              <th>Email</th>
              <th>Lý do</th>
              <th>Thực hiện bởi</th>
              <th>Thời điểm</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id}>
                <td>{log.id}</td>
                <td>{log.username}</td>
                <td>{log.email}</td>
                <td>{log.reason}</td>
                <td>{log.bannedBy}</td>
                <td>{formatTime(log.bannedAt)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!logs.length && (
          <div className={styles.empty}>Chưa có hành vi nào được ghi nhận trong lịch sử.</div>
        )}
      </div>
    </>
  );

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1>
          <Shield size={22} />
          Trang quản trị
        </h1>
        <div className={styles.actions}>
          <button type="button" className={styles.headerButton} onClick={() => navigate('/home')}>
            Về trang chủ
          </button>
          <button
            type="button"
            className={styles.headerButton}
            disabled={isRefreshing || isLoading}
            onClick={() => fetchData({ silent: true })}
          >
            <RefreshCw size={14} />
            Làm mới
          </button>
        </div>
      </div>

      <div className={styles.tabs}>
        <button
          type="button"
          className={`${styles.tab} ${activeTab === 'users' ? styles.tabActive : ''}`}
          onClick={() => setActiveTab('users')}
        >
          <Users size={15} />
          Quản lý tài khoản
        </button>
        <button
          type="button"
          className={`${styles.tab} ${activeTab === 'history' ? styles.tabActive : ''}`}
          onClick={() => setActiveTab('history')}
        >
          <Clock3 size={15} />
          Lịch sử tổng hợp
        </button>
      </div>

      {error && (
        <div className={styles.error}>
          <AlertTriangle size={16} />
          {error}
        </div>
      )}

      {isLoading ? (
        <div className={styles.loading}>Đang tải dữ liệu quản trị...</div>
      ) : (
        <div className={styles.content}>
          {activeTab === 'users' && renderUsersTable()}
          {activeTab === 'history' && renderHistory()}
        </div>
      )}
    </div>
  );
};

export default AdminDashboardPage;
