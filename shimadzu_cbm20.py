import urllib
import urllib2
from bs4 import BeautifulSoup
import re

cbm20_url = "http://192.168.200.99"
spectro_url = "http://192.168.200.98"

def _cbm20_query(cgi, data, path="/cgi-bin/"):
    req = urllib2.Request(cbm20_url+path+cgi, data)
    req.add_header('Content-Type', 'text')
    response = urllib2.urlopen(req)
    html = response.read()
    soup = BeautifulSoup(html, 'html.parser')
    return soup

def login():
    login_data="""
    <Login>
    <Mode>0</Mode>
    <Certification>
    <UserID>Admin</UserID>
    <Password>Admin</Password>
    <SessionID/>
    <Result/>
    </Certification>
    </Login>"""
    session_id = _cbm20_query("Login.cgi", login_data).find("sessionid")
    return str(session_id.text)

def logout():
    logout_data = """<Login><Mode>-1</Mode></Login>"""
    return _cbm20_query("Login.cgi", logout_data)

def switch_pump(on):
    pump_data = '<Event><Method><PumpBT>%d</PumpBT></Method></Event>' % (1 if on else 0)
    return _cbm20_query("Event.cgi", pump_data)

def start_pump():
    return switch_pump(True)

def stop_pump():
    return switch_pump(False)

def get_config():
    return _cbm20_query("Config.cgi", "<Config/>")

def select_flow_mode(mode):
    flowMode_data = """<Config><SelMode>{0}</SelMode></Config>"""
    # mode can be 'isocratic' or 'binary'(LabSolution)==LPGE
    if mode == 'isocratic':
        value = 0
    else:
        value = 3 #LPGE
    return _cbm20_query("Config.cgi", flowMode_data.format(value))

def select_solenoid_valve(valve_number):
    valve_data = """<?xml version="1.0"?>
    <Method>
    <No>0</No>
    <Alias>Method00</Alias>
    <Pumps>
    <Pump>
    <UnitID>A</UnitID>
    <Detail>
    <Psv>{0}</Psv>
    </Detail>
    </Pump>
    </Pumps>
    </Method>
    """
    return _cbm20_query("Method.cgi", valve_data.format(valve_number))

def get_flow_mode():
    cfg = get_config()
    selmode = int(cfg.find("selmode").text)
    if selmode == 0:
        # isocratic
        return "isocratic"
    elif selmode == 3:
        return "LPGE"
    else:
        return "other"
    
# before starting purge, one has to be select pump mode
# and valve position/port/'buffer bottle'
def start_autopurge():
    autopurge_data = """<?xml version="1.0"?>
    <SetUp>
    <Purge>
    <PurgeCheck>
    <ModuleSt1>{0}</ModuleSt1>
    <ModuleSt2>{1}</ModuleSt2>
    </PurgeCheck>
    <PurgeSetting>
    <SelModule1>100</SelModule1>
    <SelModule2>100</SelModule2>
    <ModuleT1>50.0</ModuleT1>
    <ModuleT2>50.0</ModuleT2>
    </PurgeSetting>
    <PurgeOther>
    <InitSt>0</InitSt>
    <InitT>10</InitT>
    <WarmSt>0</WarmSt>
    <WarmT>10</WarmT>
    </PurgeOther>
    <PurgeEvent><SelModuleNo>0</SelModuleNo><PurgeAct>1</PurgeAct></PurgeEvent></Purge>
    </SetUp>
    """
    # in isocratic mode, only module 1 has to be purged
    # in LPGE mode (binary), modules 1 and 2 have to be purged
    flow_mode = get_flow_mode()
    if flow_mode == "isocratic":
        _cbm20_query("Setup.cgi" ,'<?xml version="1.0"?><SetUp><Purge/></SetUp>')
        return _cbm20_query("Setup.cgi",  autopurge_data.format(1,0))
    elif flow_mode == "LPGE":
        _cbm20_query("Setup.cgi" ,'<?xml version="1.0"?><SetUp><Purge/></SetUp>')
        return _cbm20_query("Setup.cgi",  autopurge_data.format(1,1))
    else:
        raise RuntimeError("Invalid pump mode: %d." % selmode)

def stop_autopurge():
    _cbm20_query("Setup.cgi" ,'<?xml version="1.0"?><SetUp><Purge/></SetUp>')
    stop_autopurge_data = """<?xml version="1.0"?>
    <SetUp>
    <Purge>
    <PurgeEvent><SelModuleNo>0</SelModuleNo><PurgeAct>0</PurgeAct></PurgeEvent></Purge>
    </SetUp>
    """
    return _cbm20_query("Setup.cgi", stop_autopurge_data)

def inject_vol_from_vial(vol, vial):
    """Inject vol uL from specified vial"""
    Inject_data = """<?xml version="1.0"?>
    <Sequence><No>0</No>
    <DispStart>1</DispStart>
    <DispEnd>10</DispEnd>
    <EditStart>1</EditStart>
    <EditEnd>1</EditEnd>
    <EditType>1</EditType><TotalSeqRowNum></TotalSeqRowNum>
    <SeqRows><SeqRow>
    <RowNo>1</RowNo>
    <Rack>1</Rack>
    <Vial>
    <From>{0}</From>
    <To>{0}</To>
    </Vial>
    <InjNum>1</InjNum>
    <InjVol>{1}</InjVol>
    <SelMethodNo>0</SelMethodNo>
    <SelMethodName>Method00</SelMethodName>
    <StopTime>1.00</StopTime>
    </SeqRow>
    </SeqRows><TotalInjNum/></Sequence>"""
    seq_data = """<?xml version="1.0"?>
    <Event><Sequence><RunBT>1</RunBT></Sequence></Event>"""
    _cbm20_query("Seq.cgi", Inject_data.format(vial, vol))
    return _cbm20_query("Event.cgi", seq_data)

def stop_inject():
    seq_data = """<?xml version="1.0"?>
    <Event><Sequence><RunBT>0</RunBT></Sequence></Event>"""
    return _cbm20_query("Event.cgi", seq_data)

def set_wavelengths(w1, w2, w3, w4):
    setWavelengths_data = """<Method>
    <No>0</No>
    <PDA>
    <Usual>
    <Wave1>{0}</Wave1>
    <Wave2>{1}</Wave2>
    <Wave3>{2}</Wave3>
    <Wave4>{3}</Wave4>
    </Usual>
    </PDA>
    </Method>"""
    return _cbm20_query("Method.cgi", setWavelengths_data.format(w1,w2,w3,w4))

def get_signal_4_wavelengths():
    req = urllib2.Request(spectro_url+'/cgi-bin/login')
    req.add_header('Content-Type', 'text')
    response = urllib2.urlopen(req)
    #print "login--------------------"
    #print response.read()
    getSignal_data = """<?xml version="1.0"?> TXT_MEMO=Admin&BTN_PASSW=Admin&BTN_LOGIN=++++Login+++ """
    req = urllib2.Request(spectro_url+'/cgi-bin/logina', getSignal_data)
    response = urllib2.urlopen(req)
    #print "logina--------------------"
    #print response.read()
    req = urllib2.Request(spectro_url+'/cgi-bin/pallg', getSignal_data)
    response = urllib2.urlopen(req)
    #print "Valeurs--------------------"
    html = response.read()
    soup = BeautifulSoup(html, 'html.parser')
    all_channels = soup.findAll("font", text=re.compile('CH[1-4]'))
    #import pdb;pdb.set_trace()
    rows = [x.parent.parent.parent for x in all_channels]

    values = []
    for r in rows:
        fonts = r.findAll('font')
        txt_values = [str(f.text).strip() for f in fonts]
        values.append({ "channel": txt_values[0],
                        "wavelength": { "unit": txt_values[2],
                                        "value": float(txt_values[1]) },
                        "absorbance": { "unit": txt_values[4],
                                        "value": float(txt_values[3]) },
                        "bandwidth": { "unit": txt_values[6],
                                       "value": float(txt_values[5]) },
                        "range": txt_values[7],
                        "polarity": txt_values[8] })  
    return values


def get_monitor():
    monitor_data = '<?xml version="1.0"?><Monitor/>'
    return _cbm20_query("Monitor.cgi", monitor_data)

def get_error():
    monitor = get_monitor()
    error = monitor.find("errormon")
    return { "type": str(error.find("errortype").text),
             "code": str(error.find("errorcode").text),
             "extra": [str(x.text).split() for x in error.findAll(re.compile("errorextinfo+"))],
             "unit": str(error.find("errorunit").text) }

def set_components(a, b, c, d):
    if (a+b+c+d) != 100:
        raise ValueError("Percentage of components exceeds 100%.")
    data = """<?xml version="1.0"?><Method>
    <No>0</No>
    <Alias>Method00</Alias>
    <Pumps>
    <Pump>
    <UnitID>A</UnitID>
    <Usual>
    <Bconc>{0}</Bconc>
    <Cconc>{1}</Cconc>
    <Dconc>{2}</Dconc>
    </Usual>
    </Pump>
    </Pumps>
    </Method>"""
    return _cbm20_query("Method.cgi", data.format(b,c,d))

def get_method():
    data = '<?xml version="1.0"?><Method/>'
    return _cbm20_query("Method.cgi", data)


class Session:
    def __init__(self):
        self.id = None
    def __enter__(self):
        self.id = login()
        return self
    def __exit__(self, type, value, traceback):
        logout()
        
with Session() as session:
    print "Session id is", session.id
    #print "Starting pump"
    #print start_pump()
    #print "Stopping pump"
    #print stop_pump()
    #print get_flow_mode()



