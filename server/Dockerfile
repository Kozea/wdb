FROM python:3

ARG WDB_VERSION="3.2.4"

RUN pip install wdb.server==$WDB_VERSION
EXPOSE 19840
EXPOSE 1984
CMD ["wdb.server.py", "--detached_session"]
