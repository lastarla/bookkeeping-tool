import { apiPostForm } from './client'
import type { ImportResult } from '../types/transaction'

export function importBill(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return apiPostForm<ImportResult>('/api/import', formData)
}
