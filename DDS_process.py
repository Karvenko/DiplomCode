import get_file_names
import ctypes
from ctypes import *
import dds
# import functions #Printing
# import hands #test info

import get_file_names

#Variables - need to move to global file
VUL_NONE = 0
VUL_ALL = 1
VUL_NS = 2
VUL_EW = 3

Player_N = 0
Player_E = 1
Player_S = 2
Player_W = 3
Players = [Player_N, Player_E, Player_S, Player_W]

Suit_Spades = 0
Suit_Hearts = 1
Suit_Diamonds = 2
Suit_Clubs = 3
Suit_NT = 4

def read_pbn_line(filename='../deals_1m.pbn'):
    """Reading deals from file, one by one.
    Returns: PBN string, dealer, vulnerability"""
    dealer = -1
    vuln = -1
    
    with open(filename) as f:
        for line in f:
            
            if line[:6] == '[Deale': #Parsing dealer info
                cur_dealer = line.split('"')[1]
                if cur_dealer == 'N':
                    dealer = Player_N
                elif cur_dealer == 'E':
                    dealer = Player_E
                elif cur_dealer == 'S':
                    dealer = Player_S
                elif cur_dealer == 'W':
                    dealer = Player_W
                else:
                    dealer = -1
                    
            elif line[:6] == '[Vulne': #Parsing vulnerability
                cur_vuln = line.split('"')[1]
                if cur_vuln == 'None':
                    vuln = VUL_NONE
                elif cur_vuln == 'All':
                    vuln = VUL_ALL
                elif cur_vuln == 'NS':
                    vuln = VUL_NS
                elif cur_vuln == 'EW':
                    vuln = VUL_EW
            
            elif line[:6] == '[Deal ': #Get PBN string
                pbn_str = line.split('"')[1]
                yield pbn_str, dealer, vuln #return everything
                
            else:
                continue
                
def get_deals_batch(deal_gen, batch_size=100):
    """Put deals in batch
    Returns: PBN string array, dealer array, vulnerability array"""
    Deals = []
    Dealers = []
    Vuln = []
    
    try:
        for i in range(batch_size):
            d, ds, v = next(deal_gen)
            Deals.append(d.encode('utf-8'))
            Dealers.append(ds)
            Vuln.append(v)
    except:
        raise(StopIteration)
        
    return Deals, Dealers, Vuln

def cal_deal_batch(deal_gen, batch_size=100):
    """Calculate Double Dummy for batch
    Returns: list of trick tables, list of PAR results, DDdeals"""
    
    DDdealsPBN = dds.ddTableDealsPBN()
    tableRes = dds.ddTablesRes()
    pres = dds.allParResults()

    mode = -1 #Responcible for par calcs & Vuln. -1 - no Calc, 0 - None, 1 - Both, 2 - NS, 3 - EW
    tFilter = ctypes.c_int * dds.DDS_STRAINS
    trumpFilter = tFilter(0, 0, 0, 0, 0)
    line = ctypes.create_string_buffer(80)

    dds.SetMaxThreads(0)

    DDdealsPBN.noOfTables = batch_size
    
    Deals, Dealers, Vuln = get_deals_batch(deal_gen, batch_size)
    
    for handno in range(batch_size):
        DDdealsPBN.deals[handno].cards = Deals[handno]
        
    res = dds.CalcAllTablesPBN(ctypes.pointer(DDdealsPBN), mode, 
                               trumpFilter, ctypes.pointer(tableRes), ctypes.pointer(pres))
    
    if res != dds.RETURN_NO_FAULT:
        dds.ErrorMessage(res, line)
        print("DDS error: {}".format(line.value.decode("utf-8")))
        
    for handno in range(batch_size):
        par_res = dds.Par(ctypes.pointer(tableRes.results[handno]), 
                          ctypes.pointer(pres.presults[handno]), Vuln[handno])
        
    return tableRes, pres, DDdealsPBN, Vuln

def par_to_num(pres):
    """Converts Par from DDS internal format to NS score"""
    return int(pres.contents.parScore[0].value.decode('utf-8').split()[-1])

def resTable_to_list(resTable):
    """Converts resTable from DDS internal format to list
        North  East  South  West
    Spades 0   1     2      3
    Hearts 4   5     6      7
    Dia    8   9     10     11
    Clubs  12  13    14     15
    NT     16  17    17     19"""
    dd_table = []
    for suit in range(dds.DDS_SUITS):
        for player in Players:
            dd_table.append(resTable.contents.resTable[suit][player])
            
    for player in Players: #NT Line
        dd_table.append(resTable.contents.resTable[4][player])
        
    return dd_table

def append_batch_to_file(filename, DDdeals, Vuln, tableRes, pres, batch_size):
    with open(filename, 'a') as f:
        for i in range(batch_size):
            pbn_str = DDdeals.deals[i].cards.decode('utf-8')
            f.write('[Deal "')
            f.write(pbn_str)
            f.write('"]\n')
            
            f.write('[Vuln "%d"]\n' % Vuln[i])
            
            tricks = resTable_to_list(ctypes.pointer(tableRes.results[i]))
            f.write('[Tricks "')
            for tr in tricks:
                f.write("%d " % tr)
            f.write('"]\n')
            
            par = par_to_num(ctypes.pointer(pres.presults[i]))
            f.write('[Par "')
            f.write('%d' % par)
            f.write('"]\n\n')
            
def process_file(in_file, out_file, num_deal=10016, batch_size=32):
    """Process deals from in_file and put in out_file. 
    DO NOT CHANGE num_deals & batchsize - no error handling"""
    
    deal_count = 0
    dg = read_pbn_line(in_file)
    while deal_count < num_deal-10:
        tableRes, pres, DDdeals, Vuln = cal_deal_batch(dg, batch_size)
        append_batch_to_file(out_file, DDdeals, Vuln, tableRes, pres, batch_size)
        deal_count += batch_size
        
#         if deal_count % 640 == 0:
#             print(deal_count)

if __name__ == '__main__':
    filenames = sorted(get_file_names.get_file_names())
    print('%d files to process' % len(filenames))
    
    for name in filenames:
        get_file_names.make_lock_file(name + '.out')
        process_file(get_file_names.IN_DIR+'/' + name + '.pbn', get_file_names.OUT_DIR+'/'+name+'.out')