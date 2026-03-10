FROM kathara/base

ENV PIP_BREAK_SYSTEM_PACKAGES=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
