// src/types/shims-vue.d.ts

// 声明所有 .vue 文件
declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

// 专门解决 Element Plus 语言包找不到类型的报错
declare module 'element-plus/dist/locale/zh-cn.mjs' {
  const zhCn: any
  export default zhCn
}