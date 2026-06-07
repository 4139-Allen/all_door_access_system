<template>
  <el-dialog
    :model-value="show"
    @update:model-value="$emit('update:show', $event)"
    title="修改密码"
    width="450px"
    :close-on-click-modal="false"
  >
    <el-form
      ref="passwordFormRef"
      :model="form"
      :rules="rules"
      label-width="100px"
    >
      <el-form-item label="原密码" prop="old_password">
        <el-input v-model="form.old_password" type="password" placeholder="原密码" show-password />
      </el-form-item>
      <el-form-item label="新密码" prop="new_password">
        <el-input v-model="form.new_password" type="password" placeholder="新密码" show-password />
      </el-form-item>
      <el-form-item label="确认新密码" prop="confirm_password">
        <el-input v-model="form.confirm_password" type="password" placeholder="确认新密码" show-password />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="$emit('cancel')">取消</el-button>
      <el-button type="primary" @click="$emit('confirm')" :loading="loading">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
const props = defineProps({
  show: Boolean,
  form: Object,
  rules: Object,
  loading: Boolean
})
const emit = defineEmits(['update:show', 'cancel', 'confirm'])
const passwordFormRef = ref(null)
defineExpose({ passwordFormRef })
</script>