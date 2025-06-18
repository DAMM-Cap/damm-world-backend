from datetime import datetime

class LagoonDbDateUtils:
    @staticmethod
    def format_timestamp(ts: datetime) -> str:
        return ts.strftime('%Y-%m-%d %H:%M:%S.%f')

    @staticmethod
    def get_formatted_now() -> str:
        return LagoonDbDateUtils.format_timestamp(datetime.now())
    
    @staticmethod
    def get_datetime_formatted_now() -> datetime:
        now = datetime.now()
        return now.replace(microsecond=(now.microsecond // 1000) * 1000)

    @staticmethod
    def get_datetime_from_str(ts_str: str) -> datetime:
        return datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S.%f')