import request from '@/utils/request'

export function sendChatMessage(data) {
  return request.post('/assistant/chat', data)
}

export function getConversations() {
  return request.get('/assistant/conversations')
}

export function getConversationMessages(convId) {
  return request.get(`/assistant/conversations/${convId}/messages`)
}
