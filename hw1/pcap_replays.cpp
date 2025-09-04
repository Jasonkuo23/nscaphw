#include <arpa/inet.h> // inet_addr
#include <cstring>     // memcpy
#include <iostream>
#include <netinet/ether.h> // ethernet header struct
#include <netinet/ip.h>    // ip header struct
#include <netinet/udp.h>   // udp header struct
#include <pcap.h>          // pcap libary
#include <unistd.h>

#define MAX_PACKET_SIZE 65535

/* some useful identifiers:
 * - ETH_ALEN = 6   (ethernet address length)
 * - ETH_HLEN = 14	(ethernet header length)
*/

void modify_mac_address(struct ether_header *eth_header) {

    unsigned char src[ETH_ALEN] = {0x08, 0x00, 0x12, 0x34, 0x56, 0x78};
    memcpy(eth_header->ether_shost, src, ETH_ALEN);

    unsigned char dst[ETH_ALEN] = {0x08, 0x00, 0x12, 0x34, 0xac, 0xc2};
    memcpy(eth_header->ether_dhost, dst, ETH_ALEN);
}

void modify_ip_address(struct ip *ip_header) {

    ip_header->ip_src.s_addr = inet_addr("10.1.1.3");

    ip_header->ip_dst.s_addr = inet_addr("10.1.1.4");
}

int main() {

    char *filename = (char *)"test.pcap";
    char errbuf[PCAP_ERRBUF_SIZE];
    pcap_t *handle = pcap_open_offline(filename, errbuf);

    char *dev = (char *)"lo";
    pcap_t *send_handle = pcap_open_live(dev, PCAP_ERRBUF_SIZE, 1, 1000, errbuf);

    struct pcap_pkthdr *header;
    const u_char *packet;

    struct timeval prev = {0, 0};
    int in = 1;

    while(pcap_next_ex(handle, &header, &packet) >= 0 && packet != NULL){

        pcap_sendpacket(send_handle, packet, header->len);

        u_char *new_packet = new u_char[header->caplen];

        struct ether_header *eth_header = (struct ether_header *)new_packet;
        memcpy(new_packet, packet, header->caplen);
        modify_mac_address(eth_header);

        if (ntohs(eth_header->ether_type) == ETHERTYPE_IP){
            struct ip *ip_header = (struct ip *)(new_packet + ETH_HLEN);
            modify_ip_address(ip_header);
        }

        if(!in){
            struct timeval cur = header->ts;
            usleep((cur.tv_sec - prev.tv_sec) * 1000000 + (cur.tv_usec - prev.tv_usec));
        }
        else{
            in = 0;
        }

        pcap_sendpacket(send_handle, new_packet, header->len);

        prev = header->ts;

        delete[] new_packet;
    }

    pcap_close(handle);
    pcap_close(send_handle);
    
    return 0;
}
