FROM python:3.9

RUN pip install --upgrade pip

RUN pip install line-bot-sdk

WORKDIR /app

# install required libraries

RUN cd /tmp \
  && wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz \
  && tar -xvf ta-lib-0.4.0-src.tar.gz \
  && cd ta-lib \
  && ./configure --prefix=/usr \
  && (make -j4 || make) \
  && make install \
  && rm -rf /tmp/*

COPY . /app
RUN pip install --no-cache-dir -r requirements.txt

CMD python main.py