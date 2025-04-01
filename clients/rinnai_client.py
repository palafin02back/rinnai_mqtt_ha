import ssl
import json
import logging
import threading
from .mqtt_client import MQTTClientBase
from processors.message_processor import MessageProcessor


class RinnaiClient(MQTTClientBase):
    def __init__(self, config, message_processor: MessageProcessor):
        super().__init__(f"{config.RINNAI_USERNAME}")
        self.config = config
        self.message_processor = message_processor
        self.topics = config.get_rinnai_topics()
        self.connected = False
        self.update_timer = None
        self.disconnect_timer = None
        logging.info(f"Rinnai topics: {self.topics}")
        logging.info(f"Rinnai client 当前连接状态: {self.connected}")

        # Configure TLS
        self.client.tls_set(
            cert_reqs=ssl.CERT_NONE,
            tls_version=ssl.PROTOCOL_TLSv1_2
        )
        self.client.tls_insecure_set(True)
        self.client.username_pw_set(
            self.config.RINNAI_USERNAME, self.config.RINNAI_PASSWORD)

    def schedule_update(self):
        """定时更新任务"""
        self.connect_and_update()
        self.update_timer = threading.Timer(
            self.config.RINNAI_UPDATE_INTERVAL, self.schedule_update)
        self.update_timer.start()

    def connect_and_update(self):
        """连接并获取更新"""
        if not self.connected:
            logging.info(f"Rinnai client 开始连接，当前状态: {self.connected}")
            self.connect(self.config.RINNAI_HOST, self.config.RINNAI_PORT)
            self.connected = True
            logging.info(f"Rinnai client 连接完成，当前状态: {self.connected}")
            # 设置断开连接定时器
            if self.disconnect_timer:
                self.disconnect_timer.cancel()
            self.disconnect_timer = threading.Timer(
                self.config.RINNAI_CONNECT_TIMEOUT, self.disconnect_and_cleanup)
            self.disconnect_timer.start()
            logging.info(f"已设置 {self.config.RINNAI_CONNECT_TIMEOUT} 秒后自动断开")

    def disconnect_and_cleanup(self):
        """断开连接并清理"""
        if self.connected:
            logging.info(f"Rinnai client 开始断开连接，当前状态: {self.connected}")
            self.disconnect()
            self.connected = False
            logging.info(f"Rinnai client 断开连接完成，当前状态: {self.connected}")

    def send_command(self, action, *args):
        """
        根据命令类型调用不同的方法
        action: 命令类型，如'temp'或'mode'
        args: 参数列表
        """
        self.connect_and_update()

        if action == "temp":
            # args[0]是heat_type, args[1]是temperature值
            heat_type = args[0]
            temperature = args[1]
            self.set_temperature(heat_type, temperature)
        elif action == "mode":
            # 处理模式切换，args[0]是mode名称，args[1]是payload(ON/OFF)
            mode = args[0]
            payload = args[1] if len(args) > 1 else None
            self.set_mode(mode)
        else:
            # 如果是其他命令，直接发布到相应主题
            topic = action
            payload = args[0] if args else ""
            self.publish(topic, payload)

    def stop(self):
        """停止所有定时器"""
        logging.info("Rinnai client 开始停止所有定时器")
        if self.update_timer:
            self.update_timer.cancel()
        if self.disconnect_timer:
            self.disconnect_timer.cancel()
        self.disconnect_and_cleanup()
    
    def on_connect(self, client, userdata, flags, rc):
        """
        rc 值含义：
        0: 连接成功
        1: 协议版本错误
        2: 无效的客户端标识
        3: 服务器无法使用
        4: 错误的用户名或密码
        5: 未授权
        """
        rc_messages = {
            0: "连接成功",
            1: "协议版本错误",
            2: "未知",
            3: "服务器无法使用",
            4: "无效的客户端标识",
            5: "未授权"
        }
        message = rc_messages.get(rc, f"未知错误 {rc}")
        logging.info(f"Rinnai MQTT连接状态: {message}")
        if rc == 0:
            logging.info("开始订阅主题...")
            for topic in self.topics.values():
                self.subscribe(topic)
                logging.debug(f"已订阅主题: {topic}")
            logging.info("所有主题订阅完成")
        
        # self.set_default_status()
        


    def on_message(self, client, userdata, msg):
        try:
            logging.info(
                f"Rinnai msg topic: {msg.topic}, payload: {json.loads(msg.payload.decode('utf-8'))}")
            self.message_processor.process_message(msg)
        except Exception as e:
            logging.error(f"Rinnai message error: {e}")

    def set_temperature(self, heat_type, temperature):
        if not heat_type:
            raise ValueError("Error: heat type not specified")

        request_payload = {
            "code": self.config.AUTH_CODE,
            "enl": [
                {
                    "data": hex(temperature)[2:].upper().zfill(2),
                    "id": heat_type
                }
            ],
            "id": self.config.DEVICE_TYPE,
            "ptn": "J00",
            "sum": "1"
        }
        self.publish(self.topics["set"], json.dumps(request_payload), qos=1)
        logging.info(f"Set {heat_type} temperature to {temperature}°C")

    def set_mode(self, mode):
        if not mode:
            raise ValueError("Error: mode not specified")
        
        # 确保 mode 是字符串而不是列表
        if isinstance(mode, list):
            mode = mode[0]

        request_payload = {
            "code": self.config.AUTH_CODE,
            "enl": [
                {
                    "data": "31",
                    "id": mode
                }
            ],
            "id": self.config.DEVICE_TYPE,
            "ptn": "J00",
            "sum": "1"
        }
        self.publish(self.topics["set"], json.dumps(request_payload), qos=1)
        logging.info(f"Set mode to: {mode}")

    def set_default_status(self):
        default_status = {'enl': []}
        for key, value in self.config.INIT_STATUS.items():
            default_status['enl'].append({'id': key, 'data': value})
        self.message_processor._process_device_info(default_status)
        self.message_processor.notify_observers()
