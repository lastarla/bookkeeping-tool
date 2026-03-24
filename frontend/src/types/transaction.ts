export interface Transaction {
  id: number
  trade_date: string
  amount: number
  direction: string
  category: string | null
  transaction_type: string | null
  owner: string
  platform: string | null
  source_type: string
  source_file: string
  currency: string
  note: string | null
}

export interface ImportResult {
  status: string
  batch_id?: number
  file_name: string
  owner?: string
  platform?: string | null
  total_rows?: number
  imported_rows?: number
  skipped_rows?: number
}
