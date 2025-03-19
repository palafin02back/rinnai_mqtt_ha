
# 林内 MQTT Home Assistant 集成

本项目旨在桥接林内智能设备与 Home Assistant，目前已在 `RBS-**G56系列` (设备 ID: `0F06000C`) 上进行测试。对于其他型号的林内设备，可能需要根据设备抓包信息自行添加 MQTT 主题。

## ⚠️ 注意：订阅过多存在封号风险！ ⚠️
https://github.com/palafin02back/rinnai_mqtt_ha/issues/22
- 请注意！目前发现订阅数量过多，可能触发封禁，返回rc：5
- 建议先暂停使用，观察一段时间，被封了可以先换个账号绑定，以免影响正常app使用



## 项目背景

该项目起源于想要在Home Assistant中管理锅炉启停数据并控制，尝试抓包解包林内app数据实现home assistant中控制锅炉。对于 `RBS-**G56` 系列设备，理论上可以直接使用林内账号密码进行连接，无需手动抓包配置 MQTT 主题。

## 功能特性

- **状态监控:** 在 Home Assistant 中查看林内锅炉的运行状态。
- **温度控制:**  在 Home Assistant 中调整锅炉的温度设置。
- **燃气用量:**  获取林内锅炉的燃气消耗量数据。
- **本地 MQTT 支持:**  支持配置用户名和密码连接本地 MQTT Broker。

## 快速开始

### 环境变量

请配置以下环境变量：

```
- RINNAI_USERNAME=你的林内智家账号
- RINNAI_PASSWORD=你的林内智家密码
- LOCAL_MQTT_HOST=你的 Home Assistant MQTT Broker 地址
- LOCAL_MQTT_PORT=你的 Home Assistant MQTT Broker 端口
- LOCAL_MQTT_USERNAME=你的 Home Assistant MQTT Broker 用户名 (可选)
- LOCAL_MQTT_PASSWORD=你的 Home Assistant MQTT Broker 密码 (可选)
- LOCAL_MQTT_TLS=True 或 False (如果本地 MQTT 地址是 HTTPS，请设置为 True，默认为 False)
- LOGGING=True 或 False (是否开启日志，默认为 True)
```

### Docker 运行

```bash
docker run -d \
  --restart always \
  -e RINNAI_USERNAME=yourphone \
  -e RINNAI_PASSWORD=yourpassword \
  -e LOCAL_MQTT_HOST=yourhamqtt \
  -e LOCAL_MQTT_PORT=yourhamqttport \
  -e LOCAL_MQTT_USERNAME=test \
  -e LOCAL_MQTT_PASSWORD=test \
  -e LOCAL_MQTT_TLS=False \
  -e LOGGING=True \
  ghcr.io/palafin02back/rinnai_mqtt_ha:release
```

### Docker Compose

```yaml
version: "3.8"
services:
  rinnai_mqtt:
    image: ghcr.io/palafin02back/rinnai_mqtt_ha:release
    restart: always
    environment:
      - RINNAI_USERNAME=yourphone
      - RINNAI_PASSWORD=yourpassword
      - LOCAL_MQTT_HOST=yourhamqtt
      - LOCAL_MQTT_PORT=yourhamqttport
      - LOCAL_MQTT_USERNAME=test
      - LOCAL_MQTT_PASSWORD=test
      - LOCAL_MQTT_TLS=False
      - LOGGING=True
```

## 工作原理

本项目通过以下步骤将林内设备集成到 Home Assistant：

1. **连接林内 MQTT:** 使用配置的用户名和密码连接林内官方的 MQTT 服务器。
2. **数据处理:**  接收并解析林内 MQTT 服务器推送的消息。
3. **发布到本地 MQTT:** 将解析后的设备状态和数据发布到您配置的本地 MQTT Broker。
4. **Home Assistant 自动发现:** Home Assistant 通过 MQTT 自动发现集成的林内设备。

## 效果展示

Home Assistant 中 MQTT 可以自行发现：

![image](https://github.com/user-attachments/assets/4ec03ab1-56ab-4574-9f59-13eea7ad464c)
