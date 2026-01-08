import logging
import numpy as np

logger: logging.Logger = logging.getLogger(__name__)


class DensityCalculator:
    """Класс для расчёта крупных объёмов в ордербуке."""

    def detect_large_volumes(
            self, order_book: dict[str, list], symbol: str, threshold_factor: float = 8.0
    ) -> list[dict]:
        """Определяет заявки с объёмом, в threshold_factor раз выше среднего."""
        density_list = []

        for side in ['bids', 'asks']:
            volumes = [price * volume for price, volume in order_book.get(side, [])]
            if not volumes:
                logger.warning(f"Ордербук для {symbol} ({side}) пустой")
                continue

            avg_volume = np.mean(volumes)
            threshold = avg_volume * threshold_factor

            for price, volume in order_book.get(side, []):
                if price <= 0:
                    logger.error(f"Обнаружена некорректная цена {price} для {symbol} ({side})")
                    continue
                volume_usdt = price * volume
                if volume_usdt >= threshold:
                    density = {
                        'side': side,
                        'price': price,
                        'volume': volume,
                        'volume_usdt': volume_usdt,
                        'symbol': symbol
                    }
                    density_list.append(density)
                    logger.info(
                        f"Крупный объём ({side}) для {symbol}: {volume:.2f} лотов по {price} (USDT: {volume_usdt:.2f})"
                    )

        return density_list
