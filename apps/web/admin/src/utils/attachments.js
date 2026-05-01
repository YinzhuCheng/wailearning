import { http } from '@/api'

export const MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024

const BLOCKED_ATTACHMENT_EXTENSIONS = ['.apk', '.app', '.bat', '.cmd', '.com', '.exe', '.msi', '.ps1', '.scr']

export const attachmentHintText =
  '支持压缩包、Office 文档、PDF、TXT、图片、Jupyter 笔记本（.ipynb）等常见格式，禁止 .exe，可选，最大 20 MB。'

export const validateAttachmentFile = file => {
  if (!file) {
    return { valid: false, message: '请选择一个附件文件。' }
  }

  const fileName = file.name || ''
  const extension = fileName.includes('.') ? fileName.slice(fileName.lastIndexOf('.')).toLowerCase() : ''

  if (BLOCKED_ATTACHMENT_EXTENSIONS.includes(extension)) {
    return { valid: false, message: '不支持上传可执行文件。' }
  }

  if (file.size > MAX_ATTACHMENT_SIZE) {
    return { valid: false, message: '附件大小不能超过 20 MB。' }
  }

  return { valid: true }
}

const resolveAttachmentName = (attachmentUrl, attachmentName) => {
  const normalizedName = (attachmentName || '').trim().split(/[\\/]/).pop()
  if (normalizedName) {
    return normalizedName
  }

  try {
    const url = new URL(attachmentUrl, window.location.origin)
    const pathname = url.pathname || ''
    const storedName = pathname.split('/').filter(Boolean).pop()
    return storedName ? decodeURIComponent(storedName) : 'attachment'
  } catch {
    return 'attachment'
  }
}

export const downloadAttachment = async (attachmentUrl, attachmentName) => {
  if (!attachmentUrl) {
    return
  }

  const blob = await http.get('/files/download', {
    params: {
      attachment_url: attachmentUrl,
      ...(attachmentName ? { attachment_name: attachmentName } : {})
    },
    responseType: 'blob',
    timeout: 0
  })

  const objectUrl = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = resolveAttachmentName(attachmentUrl, attachmentName)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 1000)
}

/** Authorization header applied via http interceptor; returns a blob: URL to revoke when done. */
export const fetchAttachmentBlobUrl = async attachmentUrl => {
  if (!attachmentUrl) {
    return ''
  }
  const blob = await http.get('/files/download', {
    params: { attachment_url: attachmentUrl },
    responseType: 'blob',
    timeout: 0
  })
  return URL.createObjectURL(blob)
}
