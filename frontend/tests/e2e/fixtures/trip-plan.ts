import type { TripPlan } from '../../../src/types'

export const sampleTripPlan: TripPlan = {
  city: '杭州',
  start_date: '2026-04-03',
  end_date: '2026-04-05',
  overall_suggestions: '春季适合轻装出行，西湖周边建议以步行为主，夜晚保留一段自由活动时间。',
  budget: {
    total_attractions: 280,
    total_hotels: 960,
    total_meals: 420,
    total_transportation: 160,
    total: 1820
  },
  weather_info: [
    {
      date: '2026-04-03',
      day_weather: '多云',
      night_weather: '晴',
      day_temp: 23,
      night_temp: 15,
      wind_direction: '东北风',
      wind_power: '3级'
    },
    {
      date: '2026-04-04',
      day_weather: '晴',
      night_weather: '晴',
      day_temp: 25,
      night_temp: 16,
      wind_direction: '东风',
      wind_power: '2级'
    },
    {
      date: '2026-04-05',
      day_weather: '小雨',
      night_weather: '阴',
      day_temp: 21,
      night_temp: 14,
      wind_direction: '东南风',
      wind_power: '3级'
    }
  ],
  days: [
    {
      date: '2026-04-03',
      day_index: 0,
      description: '以西湖核心景区为主线，步行串联经典视角。',
      transportation: '公共交通',
      accommodation: '西湖景区附近酒店',
      hotel: {
        name: '湖畔旅宿',
        address: '杭州市西湖区灵隐路 88 号',
        price_range: '¥320/晚',
        rating: '4.8',
        distance: '距西湖步行 10 分钟',
        type: '舒适型酒店'
      },
      attractions: [
        {
          name: '断桥残雪',
          address: '杭州市西湖区北山街',
          location: {
            longitude: 120.1552,
            latitude: 30.2595
          },
          visit_duration: 90,
          description: '清晨和傍晚都很适合拍照，适合作为西湖第一站。',
          rating: 4.9,
          ticket_price: 0
        },
        {
          name: '平湖秋月',
          address: '杭州市西湖区白堤西端',
          location: {
            longitude: 120.1466,
            latitude: 30.2577
          },
          visit_duration: 70,
          description: '视野开阔，适合慢节奏观景与休息。',
          rating: 4.7,
          ticket_price: 0
        }
      ],
      meals: [
        {
          type: 'breakfast',
          name: '湖滨早餐铺',
          description: '豆浆与葱包烩组合'
        },
        {
          type: 'lunch',
          name: '楼外楼',
          description: '主打杭帮菜'
        },
        {
          type: 'dinner',
          name: '南山路小馆',
          description: '适合晚餐后散步'
        }
      ]
    },
    {
      date: '2026-04-04',
      day_index: 1,
      description: '第二天安排人文与寺院路线，节奏稍慢。',
      transportation: '混合',
      accommodation: '西湖景区附近酒店',
      hotel: {
        name: '湖畔旅宿',
        address: '杭州市西湖区灵隐路 88 号',
        price_range: '¥320/晚',
        rating: '4.8',
        distance: '距西湖步行 10 分钟',
        type: '舒适型酒店'
      },
      attractions: [
        {
          name: '灵隐寺',
          address: '杭州市西湖区法云弄 1 号',
          location: {
            longitude: 120.1011,
            latitude: 30.2427
          },
          visit_duration: 150,
          description: '建议上午前往，避开高峰时段。',
          rating: 4.8,
          ticket_price: 75
        },
        {
          name: '飞来峰',
          address: '杭州市西湖区灵隐路法云弄',
          location: {
            longitude: 120.1001,
            latitude: 30.2436
          },
          visit_duration: 120,
          description: '石刻与山体景观兼具。',
          rating: 4.7,
          ticket_price: 45
        }
      ],
      meals: [
        {
          type: 'breakfast',
          name: '寺前素面',
          description: '清淡开胃'
        },
        {
          type: 'lunch',
          name: '法云安缦茶室',
          description: '体验静雅茶食'
        },
        {
          type: 'dinner',
          name: '龙井山脚私房菜',
          description: '搭配龙井虾仁'
        }
      ]
    }
  ]
}
