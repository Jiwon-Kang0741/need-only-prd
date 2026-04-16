export interface ApiResponse<T> {
  header: {
    responseCode: string;
    responseMessage: string;
  };
  payload: T;
  errorInfo?: {
    status: number;
    errorType: string;
    errorCode: string;
    errorMessage: string;
    details?: any;
  };
}
