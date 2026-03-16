FROM kathara/base

ENV PIP_BREAK_SYSTEM_PACKAGES=1

COPY panbgpd_controller.service /etc/systemd/system/

COPY requirements.txt /panbgp/
RUN pip install --no-cache-dir -r /panbgp/requirements.txt

COPY ./src/ /panbgp/
