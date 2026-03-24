import { useState } from 'react'
import { Alert, Button, Modal, Space, Typography, Upload, message } from 'antd'
import { UploadOutlined } from '@ant-design/icons'
import { importBill } from '../../api/import'

interface Props {
  open: boolean
  onClose: () => void
  onImported: () => void
}

export function ImportUploader({ open, onClose, onImported }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)

  const handleImport = async () => {
    if (!file) {
      message.warning('请先选择文件')
      return
    }
    setLoading(true)
    try {
      const result = await importBill(file)
      if (result.status === 'duplicate') {
        message.info(`该文件已导入过：${result.file_name}`)
      } else {
        message.success(`导入完成：${result.file_name}`)
      }
      setFile(null)
      onImported()
      onClose()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '导入失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal title="账单导入" open={open} onCancel={onClose} onOk={() => void handleImport()} okText="开始导入" confirmLoading={loading}>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Alert message="支持的文件类型：.csv / .xlsx" type="info" showIcon />
        <Typography.Text type="secondary">请选择需要导入的账单文件，导入成功后会自动刷新当前看板。</Typography.Text>
        <Upload
          accept=".csv,.xlsx"
          beforeUpload={(selectedFile) => {
            setFile(selectedFile)
            return false
          }}
          maxCount={1}
          showUploadList
        >
          <Button icon={<UploadOutlined />}>选择文件</Button>
        </Upload>
      </Space>
    </Modal>
  )
}
