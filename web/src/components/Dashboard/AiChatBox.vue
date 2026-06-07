<template>
  <el-dialog
    v-model="dialogVisible"
    width="480px"
    top="6vh"
    :show-close="false"
    :close-on-click-modal="true"
    class="ai-dialog"
    @close="handleClose"
    @opened="handleOpened"
  >
    <template #header>
      <div class="ai-header">
        <div class="header-left">
          <div class="header-avatar">AI</div>
          <div class="header-info">
            <div class="header-title">AI 智能门禁助手</div>
            <div class="header-status">
              <span class="status-dot" :class="aiStatus"></span>
              <span>{{ aiStatus === 'online' ? '在线' : '思考中...' }}</span>
            </div>
          </div>
        </div>
        <button class="header-close" @click="dialogVisible = false">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6L6 18M6 6l12 12"/>
          </svg>
        </button>
      </div>
    </template>

    <div class="chat-box" ref="chatBox">
      <div v-if="msgList.length === 0" class="chat-empty">
        <div class="empty-title">有什么可以帮你的？</div>
        <div class="empty-tips">
          <div class="tip-item" @click="sendQuickTip('打开一楼大门')">打开一楼大门</div>
          <div class="tip-item" @click="sendQuickTip('查看今天的开门记录')">查看今天的开门记录</div>
          <div class="tip-item" @click="sendQuickTip('帮我查询所有设备')">帮我查询所有设备</div>
          <div class="tip-item" @click="sendQuickTip('系统中有多少用户')">系统中有多少用户</div>
        </div>
      </div>

      <div v-for="(item, index) in msgList" :key="index" class="msg-wrap">
        <div v-if="item.role === 'ai'" class="msg-row ai-row">
          <div class="msg-avatar ai-avatar">AI</div>
          <div class="msg-content">
            <div class="msg-sender">AI 助手</div>
            <div class="msg-bubble ai-bubble">
              <div class="bubble-text">{{ item.content }}</div>
            </div>
          </div>
        </div>
        <div v-else class="msg-row user-row">
          <div class="msg-content">
            <div class="msg-sender user-sender">我</div>
            <div class="msg-bubble user-bubble">
              <div class="bubble-text">{{ item.content }}</div>
            </div>
          </div>
          <div class="msg-avatar user-avatar">U</div>
        </div>
      </div>

      <div v-if="loading" class="msg-row ai-row">
        <div class="msg-avatar ai-avatar">AI</div>
        <div class="msg-content">
          <div class="msg-sender">AI 助手</div>
          <div class="msg-bubble ai-bubble">
            <div class="typing-dots">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="chat-footer">
      <div class="input-area">
        <input
          ref="inputRef"
          v-model="userMsg"
          class="chat-input"
          placeholder="输入指令，例如：打开一楼大门"
          @keyup.enter="sendMessage"
        />
        <button
          class="send-btn"
          :class="{ 'has-text': userMsg.trim() }"
          :disabled="!userMsg.trim() || loading"
          @click="sendMessage"
        >
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
          </svg>
        </button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import request from '@/utils/request'

const props = defineProps(['visible'])
const emit = defineEmits(['update:visible'])

const dialogVisible = ref(props.visible)
const msgList = ref([])
const userMsg = ref('')
const loading = ref(false)
const aiStatus = ref('online')
const chatBox = ref(null)
const inputRef = ref(null)

watch(() => props.visible, (val) => {
  dialogVisible.value = val
})

const handleClose = () => {
  emit('update:visible', false)
}

const handleOpened = () => {
  nextTick(() => {
    inputRef.value?.focus()
  })
}

const scrollToBottom = async () => {
  await nextTick()
  if (chatBox.value) {
    chatBox.value.scrollTop = chatBox.value.scrollHeight
  }
}

const sendQuickTip = (text) => {
  userMsg.value = text
  sendMessage()
}

const sendMessage = async () => {
  const msg = userMsg.value
  if (!msg || loading.value) return
  userMsg.value = ''

  msgList.value.push({ role: 'user', content: msg })
  loading.value = true
  aiStatus.value = 'thinking'
  scrollToBottom()

  try {
    const res = await request.post('/ai/chat', { message: msg }, { timeout: 15000 })
    await new Promise(r => setTimeout(r, 400))
    msgList.value.push({
      role: 'ai',
      content: res.data?.reply || 'AI 收到了'
    })
  } catch {
    msgList.value.push({
      role: 'ai',
      content: '抱歉，AI 服务异常，请稍后重试'
    })
  } finally {
    loading.value = false
    aiStatus.value = 'online'
    scrollToBottom()
  }
}
</script>

<style scoped>
.ai-dialog :deep(.el-dialog) {
  border-radius: 12px;
  overflow: hidden;
}
.ai-dialog :deep(.el-dialog__header) {
  margin: 0;
  padding: 0;
  border-bottom: 1px solid #ebeef5;
}
.ai-dialog :deep(.el-dialog__body) {
  padding: 0;
}
.ai-dialog :deep(.el-dialog__footer) {
  display: none;
}

.ai-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-avatar {
  width: 36px;
  height: 36px;
  background: #409eff;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
}
.header-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.header-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}
.header-status {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: #909399;
}
.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #67c23a;
}
.status-dot.thinking {
  background: #e6a23c;
  animation: pulse 0.8s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
.header-close {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  color: #909399;
  display: flex;
  align-items: center;
  justify-content: center;
}
.header-close:hover {
  background: #f0f0f0;
  color: #333;
}

.chat-box {
  height: 420px;
  overflow-y: auto;
  padding: 16px 20px;
  background: #f7f8fa;
}

.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 30px 0 10px;
}
.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 20px;
}
.empty-tips {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}
.tip-item {
  padding: 10px 16px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #606266;
  transition: all 0.2s;
}
.tip-item:hover {
  border-color: #409eff;
  color: #409eff;
}

.msg-wrap {
  margin-bottom: 16px;
}
.msg-row {
  display: flex;
  gap: 10px;
}
.msg-row.ai-row {
  justify-content: flex-start;
}
.msg-row.user-row {
  justify-content: flex-end;
}
.msg-avatar {
  width: 30px;
  height: 30px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
  margin-top: 18px;
}
.ai-avatar {
  background: #409eff;
  color: #fff;
}
.user-avatar {
  background: #909399;
  color: #fff;
}
.msg-content {
  max-width: 75%;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.msg-sender {
  font-size: 12px;
  color: #909399;
  padding: 0 4px;
}
.user-sender {
  text-align: right;
}
.msg-bubble {
  padding: 10px 14px;
  border-radius: 8px;
  line-height: 1.6;
  word-wrap: break-word;
  white-space: pre-wrap;
  font-size: 14px;
}
.ai-bubble {
  background: #fff;
  color: #303133;
  border: 1px solid #ebeef5;
}
.user-bubble {
  background: #409eff;
  color: #fff;
}

.typing-dots {
  display: flex;
  gap: 4px;
  padding: 2px 0;
}
.dot {
  width: 7px;
  height: 7px;
  background: #c0c4cc;
  border-radius: 50%;
  animation: bounce 1.4s infinite;
}
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-6px); opacity: 1; }
}

.chat-footer {
  padding: 12px 20px 16px;
  border-top: 1px solid #ebeef5;
  background: #fff;
}
.input-area {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #f7f8fa;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  padding: 4px 4px 4px 16px;
}
.input-area:focus-within {
  border-color: #409eff;
}
.chat-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  color: #303133;
  padding: 8px 0;
}
.chat-input::placeholder {
  color: #c0c4cc;
}
.send-btn {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 8px;
  background: #dcdfe6;
  color: #909399;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.send-btn.has-text {
  background: #409eff;
  color: #fff;
}
.send-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
</style>
