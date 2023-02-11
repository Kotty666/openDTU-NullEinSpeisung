#!/usr/bin/python3

import requests, time, os, logging, logging.handlers, sys, json, yaml
from pathlib import Path
from requests.auth import HTTPBasicAuth


class NullEinSpeiser:
    def __init__(self):
      while True:
        config = self._getConfig()
        counter = int(round((( time.time() - start_time ) % ( 60 * config['logInterval'] )) ,0))
        if ( 0 <= counter < 5 or config['debug']):
            self.do_log = True
        else:
            self.do_log = False
        usage = self._calcPower(config['3EM'])
        production = self._calcProduction(config['openDTU'])
        activeInvCount, activeInv = self._ActiveInv(config['openDTU'])
        if activeInvCount < 1:
            if (self.do_log):
                logging.info('No Inverter Online, nothing to do.')
        else:
            if usage < production:
                if (self.do_log):
                    logging.info('Production ({}W) higher than Usage ({}W) try to Reduce Production.'.format(round(production,2),round(usage,2)))
                self._redLimit(config, usage, production, activeInv, activeInvCount)
            else:
                if (self.do_log):
                    logging.info('Production ({}W) lower than Usage ({}W) try to Increase Production.'.format(round(production,2),round(usage,2)))
                self._incLimit(config, usage, production, activeInv, activeInvCount)
        time.sleep(5)

    def _getConfig(self):
        with open('config.yaml', 'r') as stream:
            try:
                data = yaml.safe_load(stream)
            except yaml.YAMLEror as e:
                logging.error("Could not load YAML with error %s" % (e))
                data = ''
        return data

    def _getShellyData(self, ip, user, password):
        headers = {}
        headers['Content-Type'] = 'application/json'
        URL = 'http://%s/status' % ip
        try:
            r = requests.get(url = URL, timeout=30, headers=headers, auth=(user,password))
        except requests.exceptions.Timeout:
            logging.error("RequestTimeout")
        except requests.exceptions.TooManyRedirects:
            print("Too Many Redirects")
        except requests.exceptions.RequestException as e:
            logging.error("No response from Shelly - %s" % (URL))
            print(e)
        except:
            logging.error("No response from Shelly - %s" % (URL))

        try:
            shelly_data = r.json()
        except:
            shelly_data = {}
            logging.error("Got no Json Object from Shelly - %s" % (URL))

        return shelly_data

    def _calcPower(self,em_list):
        if (isinstance(em_list,dict)):
            power = 0
            for em in em_list:
                sdata = self._getShellyData(em_list[em]['ip'],em_list[em]['user'],em_list[em]['password'])
                power += sdata['total_power']
        else:
            logging.error("3EM is no dict - nothing to do. Will no exit!")
            exit(1)
        return(power)

    def _getOpenDTUData(self,ip):
        headers = {}
        headers['Content-Type'] = 'application/json'
        URL = 'http://%s/api/livedata/status' % ip
        try:
            r = requests.get(url = URL, timeout=30, headers=headers)
        except requests.exceptions.Timeout:
            logging.error("RequestTimeout")
        except requests.exceptions.TooManyRedirects:
            print("Too Many Redirects")
        except requests.exceptions.RequestException as e:
            logging.error("No response from OpenDTU - %s" % (URL))
            print(e)
        except:
            logging.error("No response from OpenDTU - %s" % (URL))

        try:
            dtu_data = r.json()
        except:
            dtu_data = {}
            logging.error("Got no Json Object from openDTU - %s" % (URL))
        return dtu_data

    def _ActiveInv(self,od_list):
        invAct = 0
        if (isinstance(od_list,dict)):
            ActiveInv = {}
            for od in od_list:
                sdata = self._getOpenDTUData(od_list[od]['ip'])
                ActiveInv[od] = {}
                i = 0
                while i < len(sdata['inverters']):
                    if ( sdata['inverters'][i]['reachable'] and sdata['inverters'][i]['producing'] ):
                        serial  = sdata['inverters'][i]['serial']
                        name    = sdata['inverters'][i]['name']
                        limit_a = sdata['inverters'][i]['limit_absolute']
                        limit_r = sdata['inverters'][i]['limit_relative']
                        power   = sdata['inverters'][i]['0']['Power']['v']
                        ActiveInv[od][serial] = {}
                        ActiveInv[od][serial]['name'] = name
                        ActiveInv[od][serial]['limit_a'] = limit_a
                        ActiveInv[od][serial]['limit_r'] = limit_r
                        ActiveInv[od][serial]['power'] = power
                        invAct += 1
                    i += 1
        else:
            logging.error("OpenDTU is no dict - nothing to do. Will now exit!")
            exit(1)
        return invAct, ActiveInv

    def _calcProduction(self,od_list):
        if (isinstance(od_list,dict)):
            production = 0
            for od in od_list:
                sdata = self._getOpenDTUData(od_list[od]['ip'])
                production += sdata['total']['Power']['v']
        else:
            logging.error("OpenDTU is no dict - nothing to do. Will now exit!")
            exit(1)
        return production

    def _setLimit(self,ip,user,password,data):
        headers = {}
        headers['Content-Type'] = 'application/json'
        URL = 'http://%s/api/limit/config' % ip
        try:
            r = requests.post(url = URL, data=json.dumps(data), timeout=30, headers=headers, auth=(user,password))
        except requests.exceptions.Timeout:
            logging.error("RequestTimeout")
        except requests.exceptions.TooManyRedirects:
            print("Too Many Redirects")
        except requests.exceptions.RequestException as e:
            logging.error("No response from OpenDTU - %s" % (URL))
            print(e)
        except:
            logging.error("No response from OpenDTU - %s" % (URL))

    def _incLimit(self,config,usage,production,ActiveInv, ActiveInvCount):
        logging.info(ActiveInv)
        if ActiveInvCount > 1:
            if usage > ActiveInv[dtu][inv]['limit_a']:
                new_lim = 100
        else:
            for dtu in ActiveInv.keys():
                for inv in ActiveInv[dtu]:
                    new_lim = 0
                    new_w_val = 0
                    if usage > ActiveInv[dtu][inv]['limit_a']:
                        new_lim = 100
                    else:
                        new_lim = int(round(100 / ActiveInv[dtu][inv]['limit_a'] * usage,0))
                    new_w_val = int(round(ActiveInv[dtu][inv]['limit_a'] * new_lim / 100,2))
                    data = {'serial': inv, "limit_type": 1, "limit_value": new_lim }
                    if(self.do_log):
                        logging.info('Increase Inverter with SN: {inv_sn} to {pct}% Output the expectet Watt Value should be {w_val}W.'.format(inv_sn = inv, pct = new_lim, w_val = new_w_val ))

    def _redLimit(self,config,usage,production,ActiveInv, ActiveInvCount):
        over_prod = round(production - usage,2)
        over_prod_pct = round(100 - ( 100 / production * usage ))
        if (self.do_log):
            logging.info('Usage: {}W Production: {}W OverProduction: {}W Over Production Percent: {}%'.format(round(usage,2),round(production,2),over_prod,over_prod_pct))
        for dtu in ActiveInv.keys():
            new_lim = 0
            for inv in ActiveInv[dtu]:
                new_w_val = round(ActiveInv[dtu][inv]['power'] * over_prod_pct / 100,2)
                new_lim = round(100 - ( 100 / ActiveInv[dtu][inv]['power'] * new_w_val ),2)
                data = {'serial': inv, "limit_type": 1, "limit_value": new_lim }
                if(self.do_log):
                    logging.info('Reducing Inverter with SN: {inv_sn} to {pct}% Output the expectet Watt Value should be {w_val}W.'.format(inv_sn = inv, pct = new_lim, w_val = new_w_val ))
                self._setLimit(config['openDTU'][dtu]['ip'], config['openDTU'][dtu]['user'],config['openDTU'][dtu]['password'],data)

if __name__ == "__main__":
    log_rotate_handler = logging.handlers.RotatingFileHandler(
        maxBytes=5*1024*1024*10,
        backupCount=2,
        encoding=None,
        delay=0,
        filename="%s/current.log" % (os.path.dirname(os.path.realpath(__file__))),
        mode='a'
    )
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.INFO,
        handlers=[
        log_rotate_handler,
    ])

    logging.info('NullEinspeisung starting up...')
    start_time = time.time()
    NullEinSpeiser()
