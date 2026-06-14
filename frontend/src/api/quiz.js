import request from '@/utils/request'

export function generateQuiz(data) {
  return request.post('/quiz/generate', data)
}

export function submitAnswer(data) {
  return request.post('/quiz/submit', data)
}

export function getQuizRecords() {
  return request.get('/quiz/records')
}

export function getWrongQuiz() {
  return request.get('/quiz/wrong')
}
