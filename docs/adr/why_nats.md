nats is a good broker because a server is available for every os (linux, mac, windows) and comes as a wrapper python package. its very fast.
it has ultra low latency, sub/pub system and is usually used in cloud native apps.

mqtt is tcp and oriented for iot. its also oriented for limited devices and edge computing.

nats allows fire and forget, what is good for low latency. mqtt has qos-1,2,3 and retained messages. nats has jetstream, which also kind of has retained messages as a key-value store

mqtt is low latency, nats is sub ms latency

nats needs more ram for jetstream (not used here) -> better for servers than for embedded. mqtt has extremely lightweight clients.

mqtt has a lighter and smaller cpu and ram usage. different implementations though. nats only one, wich is first class.

mqtt can be used, if nats does not work on android.
nats supports all os (lnux, win, mac) and also arm (32/64) and x86

# why nats in general? or why broker in general?

flexibility and seperation of concerns, allows for easy modification