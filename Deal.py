#Updated on 13.07 - bug with vuln in contract result calcs fixed
#15.07 - bug with 1x-p-p-p-p fixed
#24.07 - small slam bonus corrected from 1000 to 750
import numpy as np
import torch

#just for testing
results = [10,3,10,3,9,4,9,4,4,8,4,8,5,8,5,8,6,6,6,6]

#Constants
CONTRACT_SCORES = [[20, 40, 60, 80, 100, 120, 140], #CLUBS
                  [20, 40, 60, 80, 100, 120, 140], #Diamonds
                  [30, 60, 90, 120, 150, 180, 210], #Hearts
                  [30, 60, 90, 120, 150, 180, 210], #Spades
                  [40, 70, 100, 130, 160, 190, 220] #NT
                  ]

#Contract bonuses
PARTSCORE = 50
GAME_BONUS = (300, 500)
SMALL_BONUS = (500, 750)
GRAND_BONUS = (1000, 1500)
DOUBLE_BONUS = 50
REDOUBLE_BONUS = 100
DOUBLE_TRICK = (100, 200)
REDOUBLE_TRICK = (200, 400)

IMP_TABLE = [10, 40, 80, 120, 160, 210, 
             260, 310, 360, 420, 490,
             590, 740, 890, 1090, 1290,
             1490, 1740, 1990, 2240, 2490,
             2990, 3490, 3990, 100000]

card_dict = {
    '2' : 0,
    '3' : 1,
    '4' : 2,
    '5' : 3,
    '6' : 4,
    '7' : 5,
    '8' : 6,
    '9' : 7,
    'T' : 8,
    'J' : 9,
    'Q' : 10,
    'K' : 11,
    'A' : 12
}

bit_dict = {
    0 : '2',
    1 : '3',
    2 : '4',
    3 : '5',
    4 : '6',
    5 : '7',
    6 : '8',
    7 : '9',
    8 : 'T',
    9 : 'J',
    10 : 'Q',
    11 : 'K',
    12 : 'A'
}

suit_dict = {0 : 'C', 1 : 'D', 2 : 'H', 3 : 'S', 4 : 'NT'}
decl_dict = {0 : 'N', 1 : 'E', 2 : 'S', 3 : 'W'}

#Indexes of bids in compact bidding vector
CB_contracts = [3, 12, 21, 30, 39,
                48, 57, 66, 75, 84,
                93, 102, 111, 120, 129,
                138, 147, 156, 165, 174,
                183, 192, 201, 210, 219,
                228, 237, 246, 255, 264,
                273, 282, 291, 300, 309]

CB_doubles = [6, 15, 24, 33, 42,
              51, 60, 69, 78, 87,
              96, 105, 114, 123, 132,
              141, 150, 159, 168, 177,
              186, 195, 204, 213, 222,
              231, 240, 249, 258, 267,
              276, 285, 294, 303, 312]

CB_redoubles = [9, 18, 27, 36, 45,
                54, 63, 72, 81, 90,
                99, 108, 117, 126, 135,
                144, 153, 162, 171, 180,
                189, 198, 207, 216, 225,
                234, 243, 252, 261, 270,
                279, 288, 297, 306, 315]

CB_passes = [0, 1, 2, 4, 5, 7, 8, 10, 11, 13, 14, 16, 17, 19, 20, 22, 23, 25, 26, 28, 29,
             31, 32, 34, 35, 37, 38, 40, 41, 43, 44, 46, 47, 49, 50, 52, 53, 55, 56, 58,
             59, 61, 62, 64, 65, 67, 68, 70, 71, 73, 74, 76, 77, 79, 80, 82, 83, 85, 86,
             88, 89, 91, 92, 94, 95, 97, 98, 100, 101, 103, 104, 106, 107, 109, 110, 112,
             113, 115, 116, 118, 119, 121, 122, 124, 125, 127, 128, 130, 131, 133, 134, 136,
             137, 139, 140, 142, 143, 145, 146, 148, 149, 151, 152, 154, 155, 157, 158, 160,
             161, 163, 164, 166, 167, 169, 170, 172, 173, 175, 176, 178, 179, 181, 182, 184,
             185, 187, 188, 190, 191, 193, 194, 196, 197, 199, 200, 202, 203, 205, 206, 208,
             209, 211, 212, 214, 215, 217, 218, 220, 221, 223, 224, 226, 227, 229, 230, 232,
             233, 235, 236, 238, 239, 241, 242, 244, 245, 247, 248, 250, 251, 253, 254, 256,
             257, 259, 260, 262, 263, 265, 266, 268, 269, 271, 272, 274, 275, 277, 278, 280,
             281, 283, 284, 286, 287, 289, 290, 292, 293, 295, 296, 298, 299, 301, 302, 304,
             305, 307, 308, 310, 311, 313, 314, 316, 317, 318] #Real length of bidding - 319!!! not 318 as mentioned everywhere

VUL_NONE = 0
VUL_ALL = 1
VUL_NS = 2
VUL_EW = 3

def hand_to_vec(hand):
    """Converts text string into 52x[0,1]
    Order - SHDC, 2 - lowest, A - highest"""
    vec = [0]*52
    
    hand = hand.upper()
    
    offset = 0
    for suit in hand.split('.'):
        if len(suit) > 0:
            for card in suit:
                vec[offset + card_dict[card]] = 1
        
        offset += 13
        
    return vec

def vec_to_hand(vec):
    """Converts vector to human-readable format"""
    hand_str = ''
    
    offset = 0
    for suit in range(4):
        for card in range(12, -1, -1): #reverse walk
            if vec[offset + card] == 1:
                hand_str += bit_dict[card]
                
        offset += 13
        hand_str += '.'
    return hand_str[:-1] #remove trailing dot

class CompactBidding():
    def __init__(self):
        self.vector = np.zeros((319), dtype=np.int8)
        self.lastbid = -1
        
    def add_bid(self, bid):
        if bid < 35: #Contract
            idx = CB_contracts[bid]
        elif bid == 35: #pass
            if self.lastbid == -1: #first bid
                idx = 0
            else:
                idx = CB_passes[np.searchsorted(CB_passes, self.lastbid+1)]
        elif bid == 36: #double
            idx = CB_doubles[np.searchsorted(CB_doubles, self.lastbid+1)]
        elif bid == 37:
            idx = CB_redoubles[np.searchsorted(CB_redoubles, self.lastbid+1)]
            
        self.vector[idx] = 1
        self.lastbid = idx
        
    def bidding_to_vec(self, bidding):
        for bid in bidding:
            self.addbid(bid)
            
    def vec_to_bidding(self):
        bidding = []
        for i, bit in enumerate(self.vector):
            if bit == 1:
                if i in CB_passes:
                    bidding.append(35)
                elif i in CB_doubles:
                    bidding.append(36)
                elif i in CB_redoubles:
                    bidding.append(37)
                else:
                    bidding.append(int((i-3)/9))
        return bidding
    
class Deal:
    
    def __init__(self, PBN, vuln, res, par):
        self.PBN = PBN
        self.vuln = vuln #0 - None, 1 - All, 2 - NS, 3 - EW
        self.res_table = res
        self.par = par
        self.hands = self.get_hands_vec()
        self.bidding = []
        self.bidding_prob = []
        self.lastbid = -1
        self.doubled = 0
        self.redoubled = 0
        self.declarer = None
        self.bid_vect = CompactBidding()
        self.bidding_finished = False
        self.valid_bids = self.update_valid_bids()
        
    def get_vuln_for_declarer(self):
        if self.vuln == 0 or self.vuln == 1: #both none or both in
            return self.vuln
            
        if self.vuln == 2: #NS
            if self.declarer % 2 == 0: #NS
                return 1
            else:
                return 0
        if self.vuln == 3: #EW
            if self.declarer % 2 == 0: #NS
                return 0
            else:
                return 1
            
        
    def print_pbn(self):
        print(self.PBN)
        
    def get_hands_vec(self):
        hands_vec = []
        for cur_hand in self.PBN[2:].split(' '):
            hands_vec.append(hand_to_vec(cur_hand))
            
        return hands_vec
    
    def if_bidding_finished(self):
        if len(self.bidding) < 4:
            return False
#        elif len(self.bidding) == 4:
#            return all([x==35 for x in self.bidding[-4:]]) #First round - may have 4 passes
        else:
            return all([x==35 for x in self.bidding[-3:]]) #waiting for 3 passes
        return
    
    def add_bid(self, bid, prob=0):
        #Function do not check for bid correctness
        self.bidding.append(bid)
        self.bidding_prob.append(prob)
        self.bid_vect.add_bid(bid)
        if bid < 35: #0-34 - contracts, 35 - pass, 36 double, 37 - redouble
            self.lastbid = bid
            self.doubled = 0
            self.redoubled = 0
            self.declarer = (len(self.bidding)-1)%4
        elif bid == 36:
            self.doubled = 1
        elif bid == 37:
            self.doubled = 0
            self.redoubled = 1
            
        self.update_valid_bids()
        return
            
    def print_bidding(self):
        print('North\tEast\tSouth\tWest')
        if len(self.bidding) == 0:
            return
        
        num_rounds = len(self.bidding)//4  #number of full rounds
        char_bids = [0]*4
        for cur_round in range(num_rounds):
            cur_bids = self.bidding[cur_round*4:cur_round*4+4]
            for i, bid in enumerate(cur_bids):
                if bid == 35:
                    char_bids[i] = 'pass'
                elif bid == 36:
                    char_bids[i] = 'X'
                elif bid == 37:
                    char_bids[i] = 'XX'
                else:
                    char_bids[i] = str(int(np.ceil(bid/5+0.1))) + suit_dict[bid%5]
            print(char_bids[0]+'\t'+char_bids[1]+'\t'+char_bids[2]+'\t'+ char_bids[3])
            
        for i,bid in enumerate(self.bidding[num_rounds*4:]):
            if bid == 35:
                char_bids[i] = 'pass'
            elif bid == 36:
                char_bids[i] = 'X'
            elif bid == 37:
                char_bids[i] = 'XX'
            else:
                char_bids[i] = str(int(np.ceil(bid/5+0.1))) + suit_dict[bid%5]
        
        if len(self.bidding) % 4 > 0:
            for idx in range(i+1, 4):
                char_bids[idx] = ''

    #             print(char_bids[0])
            print(char_bids[0]+'\t'+char_bids[1]+'\t'+char_bids[2]+'\t'+ char_bids[3])
        return
                 
    def print_contract(self):
        if self.lastbid >= 0:
            contract = str(int(np.ceil(self.lastbid/5+0.1))) + suit_dict[self.lastbid%5]
            if self.doubled:
                contract += 'X'
            if self.redoubled:
                contract += 'XX'

            declarer = decl_dict[self.declarer]

            print('Contract: ', contract, 'by ', declarer) 
        else:
            print('All pass')
        return
        
    def update_valid_bids(self):
        """Returns array in the beginning, or updates it in place later"""
        bid_len = len(self.bidding)
        if bid_len == 0: #Inital call
            bids = np.ones((38), dtype=np.int8)
            bids[36] = 0 #double not possible
            bids[37] = 0 #redouble not possible
            return bids
        
        if self.bidding[-1] < 35: #Last bid - contract
            for i in range(self.bidding[-1]+1):
                self.valid_bids[i] = 0
            self.valid_bids[36] = 1
            self.valid_bids[37] = 0
        elif self.bidding[-1] == 35: #pass
            if bid_len == 1: #first bid
                return
            elif bid_len == 2: #Two bids - double or redouble not allowed (1C - PASS)
                self.valid_bids[36] = 0
                self.valid_bids[37] = 0
            elif bid_len == 3: #(X-Y-PASS) - cannot double or redouble anyway. bid array updated on previous step
                self.valid_bids[36] = 0
                self.valid_bids[37] = 0 #Cannot redouble
            else: #4 and more bids
                if self.bidding[-2] == 35: #partner passed
                    if self.bidding[-3] < 35: #LHO Bid
                        self.valid_bids[36] = 1
                        self.valid_bids[37] = 0
                    elif self.bidding[-3] == 36: #LHO doubled
                        self.valid_bids[36] = 0
                        self.valid_bids[37] = 1
                    else:
                        self.valid_bids[36] = 0
                        self.valid_bids[37] = 0
                else: #Any other partner's bid followed by pass - cannot double or redouble
                    self.valid_bids[36] = 0
                    self.valid_bids[37] = 0
        elif self.bidding[-1] == 36: #doubled
            self.valid_bids[36] = 0
            self.valid_bids[37] = 1
        elif self.bidding[-1] == 37: #redoubled
            self.valid_bids[36] = 0
            self.valid_bids[37] = 0
        return   
                    
        
    def select_bid(self, bids_probs):
        """Selects most probable VALID bid from probs and adds it to deal"""
        masked_probs = np.multiply(bids_probs, self.valid_bids)
#         print(masked_probs)
        bid = np.argmax(masked_probs)
        self.add_bid(bid, masked_probs[bid])
        return
    
    def calc_deal_result(self): #, contract, doubled, vuln, dealer, res_array):
        """Calculate score for contract (by number 0-34) based on res_array. 
        Doubled could be 0 (No), 1 (doubled), 2(redoubled).
        Vuln - 0 or 1"""
    
        if self.lastbid == -1: #All pass
            return 0
        
        contract = self.lastbid
        if self.doubled == 1:
            doubled = 1
        elif self.redoubled == 1:
            doubled = 2
        else:
            doubled = 0
        vuln = self.get_vuln_for_declarer()
        dealer = self.declarer
        res_array = self.res_table
        
        cont_tricks = int(np.ceil(contract / 5.0 + 6.1)) #6 tricks to base number, 0.1 - to handle clubs
        cont_suit = contract % 5
    #     print( cont_tricks, cont_suit)

        if cont_suit == 0: #CLubs
            real_tricks = res_array[12:16][dealer]
        elif cont_suit == 1: #diamonds
            real_tricks = res_array[8:12][dealer]
        elif cont_suit == 2: #hearts
            real_tricks = res_array[4:8][dealer]
        elif cont_suit == 3: #spades
            real_tricks = res_array[0:4][dealer]
        else: #NT
            real_tricks = res_array[16:][dealer]
        
        delta = real_tricks - cont_tricks
    #     print(real_tricks, delta)
        #print('vuln', vuln)
    
        #print('doubled: ', doubled)
        if delta < 0: #going down
            if doubled == 0: #no double, no trouble
                if not vuln:
                    result = 50 * delta
                else:
                    result = 100 * delta
            else: #doubled or redoubled
                if vuln==0:
                    if -delta == 1:
                        result = -100
                    elif -delta == 2:
                        result = -300
                    elif -delta == 3:
                        result = -500
                    else:
                        result = -500 + 300 * (delta+3)
                elif vuln == 1:
                    if -delta == 1:
                        result = -200
                    else:
                        result = -200 + 300 * (delta + 1)
            if doubled == 2: #Add redouble over double
                result *= 2
        else: #making
    #         delta = real_tricks - cont_tricks
            #Base score
            if doubled == 0: #No double
                base_score = CONTRACT_SCORES[cont_suit][cont_tricks-7]
                overtrick_score = CONTRACT_SCORES[cont_suit][real_tricks-7] - CONTRACT_SCORES[cont_suit][cont_tricks-7]
            elif doubled == 1: #doubled
                base_score = CONTRACT_SCORES[cont_suit][cont_tricks-7] * 2
                overtrick_score = DOUBLE_BONUS + DOUBLE_TRICK[vuln] * delta
            elif doubled == 2: #redoubled
                base_score = CONTRACT_SCORES[cont_suit][cont_tricks-7] * 4
                overtrick_score = REDOUBLE_BONUS + REDOUBLE_TRICK[vuln] * delta

            #COntract Bonuses
            if base_score < 100: #Partscore
                bonus = 50
            else:
                bonus = GAME_BONUS[vuln]

            if cont_tricks == 12:
                bonus += SMALL_BONUS[vuln]
            elif cont_tricks == 13:
                bonus += GRAND_BONUS[vuln]

            result = base_score + overtrick_score + bonus
        #Always return result for NS   
        if dealer == 0 or dealer == 2:
            return result
        else:
            return -result
        
    def imp_count(self): #score, par):
        delta = self.calc_deal_result() - self.par

        imp = np.searchsorted(IMP_TABLE, np.abs(delta))
        return np.sign(delta) * imp
    
    def form_static_vec(self, player):
        
        if self.vuln == 1: #All
            vuln = [1, 1]
        elif self.vuln == 1: #NS
            vuln == [1, 0]
        elif self.vuln == 2: #EW
            vuln = [0, 1]
        else:
            vuln = [0, 0]
            
        return np.int8(np.hstack((self.hands[player], vuln, self.bid_vect.vector)))
            
#     def get_enn_output(self, player, enn):
#         """Returns feature vector with output from ENN"""
        
#         vec = self.form_static_vec(player)
#         return np.int8(np.hstack((vec, enn(torch.Tensor(vec)))))
    
def read_deal_from_file(filename='../deals_processed/11000.out'):
    """Reading deals from file, one by one.
    Returns: PBN string, vulnerability, contract table, Par score"""
    dealer = -1
    vuln = -1
    
    with open(filename) as f:
        for line in f:
            if line[:6] == '[Deal ':
                pbn_str = line.split('"')[1]
            elif line[:6] == '[Vuln ':
                vuln = int(line.split('"')[1])
            elif line[:6] == '[Trick':
                results = [int(x) for x in line.split('"')[1].split(' ')[:-1]]
            elif line[:6] == '[Par "':
                par = int(line.split('"')[1])
                yield pbn_str, vuln, results, par
                
def load_deals(filename='../deals_processed/11000.out'):
    """Loads deals from file. """
    deals = []
    gen = read_deal_from_file(filename)
    
    for a in gen:
        deals.append(Deal(a[0], a[1], a[2], a[3]))
        
    return deals