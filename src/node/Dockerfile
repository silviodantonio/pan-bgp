FROM kathara/frr

ENV PIP_BREAK_SYSTEM_PACKAGES=1

COPY requirements.txt /panbgp/
RUN pip install --no-cache-dir -r /panbgp/requirements.txt

COPY . /panbgp
