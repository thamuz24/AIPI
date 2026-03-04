import axios from 'axios';

export function getApiErrorMessage(error, fallbackMessage = 'Có lỗi xảy ra. Vui lòng thử lại.') {
  if (!error) return fallbackMessage;

  if (axios.isAxiosError(error)) {
    const responseMessage = error.response?.data?.message;
    if (typeof responseMessage === 'string' && responseMessage.trim()) {
      return responseMessage;
    }

    if (error.response?.status === 401) {
      return 'Thông tin đăng nhập không hợp lệ.';
    }

    if (error.code === 'ECONNABORTED') {
      return 'Yêu cầu hết thời gian. Vui lòng thử lại.';
    }

    return 'Không thể kết nối đến aipa_core. Hãy kiểm tra backend và biến REACT_APP_API_BASE_URL.';
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallbackMessage;
}
