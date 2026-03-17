export const TRANSPORTATION_OPTIONS = [
  { value: '公共交通', label: '公共交通', emoji: '🚇', detail: '优先地铁、公交与步行换乘' },
  { value: '自驾', label: '自驾', emoji: '🚗', detail: '更自由，适合多点穿梭' },
  { value: '步行', label: '步行', emoji: '🚶', detail: '慢节奏探索，适合短距离城区' },
  { value: '混合', label: '混合', emoji: '🧭', detail: '按场景自动组合多种方式' }
] as const

export const ACCOMMODATION_OPTIONS = [
  { value: '经济型酒店', label: '经济型酒店', emoji: '🛏️', detail: '控制预算，满足基础住宿' },
  { value: '舒适型酒店', label: '舒适型酒店', emoji: '🏨', detail: '平衡体验与价格' },
  { value: '豪华酒店', label: '豪华酒店', emoji: '✨', detail: '更强调设施与服务体验' },
  { value: '民宿', label: '民宿', emoji: '🏡', detail: '更有在地生活感' }
] as const

export const PREFERENCE_OPTIONS = [
  { value: '历史文化', label: '历史文化', emoji: '🏛️' },
  { value: '自然风光', label: '自然风光', emoji: '🌿' },
  { value: '美食', label: '美食', emoji: '🍜' },
  { value: '购物', label: '购物', emoji: '👜' },
  { value: '艺术', label: '艺术', emoji: '🎨' },
  { value: '休闲', label: '休闲', emoji: '☕' }
] as const

export const LOADING_PHASES = [
  '正在初始化行程草稿...',
  '正在搜索景点与路线...',
  '正在整理天气与住宿建议...',
  '正在生成每日安排...'
]

export const RESULT_SECTIONS = {
  overview: '行程概览',
  budget: '预算明细',
  map: '景点地图',
  weather: '天气信息'
} as const
