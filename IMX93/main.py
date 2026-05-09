"""Edge pipeline entry on FRDM-IMX93.

Polls the wake-word and pose-skeleton detectors. When either reports danger
(output==1), hands off to double_check.confirm() which gives the user a
10-second cancel window before notifying the family via the GCF endpoint.
"""
import time

from 喚醒詞 import getter as wake_getter
from 骨架 import getter as pose_getter

from double_check import confirm

POLL_INTERVAL_S = 0.1


def main() -> None:
    while True:
        if wake_getter() == 1:
            confirm(event_type="help")
        elif pose_getter() == 1:
            confirm(event_type="fall")
        time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    main()
