export const channelIcons: Record<string, string> = {
  dingtalk: new URL('../assets/icons/dingtalk.png', import.meta.url).href,
  feishu: new URL('../assets/icons/feishu.png', import.meta.url).href,
  wechat: new URL('../assets/icons/wechat.png', import.meta.url).href,
  gitlab: new URL('../assets/icons/gitlab.png', import.meta.url).href
}

export const channelTypeLabels: Record<string, string> = {
  dingtalk: '钉钉通知',
  feishu: '飞书通知',
  wechat: '企业微信通知',
  slack: 'Slack 通知',
  gitlab: 'GitLab 评论',
  email: '邮件通知'
}
