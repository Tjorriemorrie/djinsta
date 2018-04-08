docker run -p 9200:9200 -p 9300:9300 -e "discovery.type=single-node" --name="djinsta" docker.elastic.co/elasticsearch/elasticsearch-oss:6.2.3
