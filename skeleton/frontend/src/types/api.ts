export interface ApiResponseHeader {
  responseCode: string
  responseMessage: string
}

export interface ApiResponse<T = unknown> {
  header: ApiResponseHeader
  payload: T
}
