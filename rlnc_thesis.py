#!/usr/bin/env python
# encoding: utf-8

# License for Commercial Usage
# Distributed under the "PYERASURE EVALUATION LICENSE 1.3"
# Licensees holding a valid commercial license may use this project in
# accordance with the standard license agreement terms provided with the
# Software (see accompanying file LICENSE.rst or
# https://www.steinwurf.com/license), unless otherwise different terms and
# conditions are agreed in writing between Licensee and Steinwurf ApS in which
# case the license will be regulated by that separate written agreement.
#
# License for Non-Commercial Usage
# Distributed under the "PYERASURE RESEARCH LICENSE 1.2"
# Licensees holding a valid research license may use this project in accordance
# with the license agreement terms provided with the Software
# See accompanying file LICENSE.rst or https://www.steinwurf.com/license

import os
import random
import time

import pyerasure
import pyerasure.finite_field
import pyerasure.generator

import sys
import math
import copy


useful_symbol = 0 #Counter that increases the symbols useful for decoding.
key_id_index=1  # ID of the symbols
counter_for_slots=0 #Timer for the transmission time of packets in slots
sent_source_symbol=0 #Finds how many packets coefficients need to be created for(for min_encode_symbol).
correct_sent_not_in_order=[] #The symbols that are sent correctly but are located after some lost symbol.
num_of_lost_symbols=0 #The number of lost symbols.
num_of_coded_i_need=0 #The coded symbols needed for decoding.
pending_list_required=True #To identify which correct sentnot in order symbols are in queue (used for average in-order delay).
decoding_matrix_per_group={}

def urandom_from_random(seed, length):
    rng = random.Random()
    rng.seed(seed)
    return bytearray([rng.randint(0,255) for i in range(length)])


class CustomEncoder(pyerasure.Encoder):
    def __init__(self, field, symbols, symbol_bytes):
        super().__init__(field, symbols, symbol_bytes)
        self.systematic_index = 0

#Saves the start time of each symbol.
def add_start_time(time_hashmap, obj_index, start_time):
    if obj_index not in time_hashmap:
        time_hashmap[obj_index] = []
    time_hashmap[obj_index].append(start_time)
    return time_hashmap


def get_integer_input(prompt):
    while True:
        try:
            value = int(input(prompt))
            return value
        except ValueError:
            print("Invalid input. Please enter an integer.")


def print_dict_keys_and_values(time_hashmap):
    sorted_keys = sorted(time_hashmap.keys())  
    for key in sorted_keys:
        value = time_hashmap[key]
        print(f"Key: {key}, Value: {value}")



#create systematic symbols 
def process_systematic_symbol(encoder, decoder, loss_probability, systematic_index, time_hashmap,lost_symbols,pending_symbols):
    global  counter_for_slots, key_id_index,sent_source_symbol,correct_sent_not_in_order,num_of_lost_symbols, pending_list_required

    print("Systematic symbol", end="")

    index = systematic_index

     
    symbol = encoder.symbol_data(index)
    start_time = counter_for_slots
    

    sent_source_symbol+=1

    # Drop packet based on loss probability
    if random.uniform(0.0, 100.0) < loss_probability:
        print(" - lost")
        lost_symbols.append(key_id_index)
        add_start_time(time_hashmap, key_id_index,start_time)
        num_of_lost_symbols+=1
       
     
        
    else:
        
        decoder.decode_systematic_symbol(symbol, systematic_index)
       
        print(f" - decoded, rank now {decoder.rank}")
      

     #pending list for folllowing symbols after a dropped symbol
    if  pending_list_required:
        if lost_symbols and key_id_index > lost_symbols[0]:
            pending_symbols.append(key_id_index)
  
  

    correct_sent_not_in_order = [item for item in pending_symbols if item not in lost_symbols]
    
    
   
    if pending_symbols or lost_symbols:
        add_start_time(time_hashmap, key_id_index,start_time)

    else:
        end_time = counter_for_slots
       
        add_start_time(time_hashmap, key_id_index,end_time-start_time)
    counter_for_slots+=1

    
    key_id_index+=1
  
       

 

#here create coded symbols
def process_coded_symbol(encoder, decoder,generator,loss_probability,time_hashmap,decoding_matrix_values,lost_symbols,pending_symbols,systematic_index,generation_size,decoding_matrix_values2):
    
    global counter_for_slots,key_id_index,sent_source_symbol,num_of_lost_symbols,num_of_coded_i_need,correct_sent_not_in_order, pending_list_required
    print("Coded symbol", end="")
    
    #coefficients for all the generation
    coefficients2 = generator.generate()
   
    
    #Coefficients only for the systematic symbols that have been received so far
    coefficients = generator.generate_partial(sent_source_symbol)
    
    
    num_zeros_to_add2 = len(coefficients2) - len(coefficients)
    
    # set coefficients to zero for the systematic symbols that have not been sent yet.
    if num_zeros_to_add2 > 0:
        coefficients+= bytearray([0] * num_zeros_to_add2)

    symbol=encoder.min_encode_symbol(coefficients,sent_source_symbol)
  
    
   

    # Drop packet based on loss probability
    if random.uniform(0.0, 100.0) < loss_probability:
        print(" - lost")
        counter_for_slots+=1
      

    else:
       
       
        num_of_coded_i_need+=1
       
       
        decoder.decode_symbol(symbol, bytearray(coefficients))
       
        print(f" - decoded, rank now {decoder.rank}")
   
        
        #checks if decoding is possible        
        if num_of_lost_symbols==num_of_coded_i_need:
            pending_and_lost_symbols=list(set(lost_symbols+pending_symbols))
            pending_and_lost_symbols.sort()
            decoding_matrix_values.append(decoder.rank)
            decoding_matrix_values2.append(decoder.rank)
            for key in pending_and_lost_symbols:
               
                if key in time_hashmap:
                    
                    start_time = time_hashmap[key][0]
                    end_time = counter_for_slots
                    new_value = end_time - start_time
                    time_hashmap[key] = [new_value]
                    if key in lost_symbols:
                        lost_symbols.remove(key) 
                    if key in pending_symbols:
                        pending_symbols.remove(key) 
            pending_list_required=False
            
            num_of_coded_i_need=0
            num_of_lost_symbols=0

        if num_of_lost_symbols==0:
            num_of_coded_i_need=0
        counter_for_slots+=1
    




#It creates subgroups within each group, based on the number of uncoded symbols sent before the coded ones
def create_subgroups(group, symbols_per_subgroup):
    subgroups = []

    for i in range(0, len(group), symbols_per_subgroup):
        subgroup = group[i:i + symbols_per_subgroup]
        subgroups.append(subgroup)

    return subgroups



def main(argv):
    
    pending_symbols=[] #symbols that are located after a lost symbol in the same generation.
    status={}
    if len(argv) < 1:
        print("You need to provide a number (seed) to run the program.")
        sys.exit(1)

    seed=int(sys.argv[1])
    random.seed(seed)


    global key_id_index,sent_source_symbol,useful_symbol,correct_sent_not_in_order,num_of_coded_i_need, pending_list_required,num_of_lost_symbols
     
    # Pick the finite field to use for the encoding and decoding.
    field = pyerasure.finite_field.Binary8()

    time_hashmap={}
    
    # Pick the number of symbols to encode/decode.κα
    symbols = get_integer_input("Enter the symbols: ")

    #symbols = 15

   
    # Pick the size of each symbol in bytes
    symbol_bytes = 1400
    
    generation_size=get_integer_input("Enter the generation size: ")


     # Lose packets with 10% probability
    while True:
        loss_probability = input("Enter loss probability (float): ")

        try:
        
            loss_probability = float(loss_probability)
            break
        except ValueError:
            print("Invalid input. Please enter a numeric float value.")

    while True:
        code_rate = input("Enter code rate (e.g. 4/5): ")

        try:
    
            rate_of_systematic_symbol, denominator = map(int, code_rate.split('/'))
            #print("rate_of_systematic_symbol:", rate_of_systematic_symbol)
            #print("Denominator:", denominator)
            rate_of_coded_symbol = denominator - rate_of_systematic_symbol


            break
        except ValueError:
            print("Invalid input. Please enter a numeric fraction .")
    while True:
        drop_gen = input("Choose the packet managment mechanism (1 for drop out of order or 2 for drop generation): ")

        try:
        
            drop_gen = int(drop_gen)
            if drop_gen != 1 and drop_gen != 2:
                print("Invalid input. Please enter 1 or 2.")
                continue 
            break
        except ValueError:
            print("Invalid input. Please enter a numeric integer value.")
    
  
    #code rate
    R = rate_of_systematic_symbol/denominator
    
    if symbols==0:
        print("You have 0 symbols. ")
        sys.exit(0)
    else:
    #------------------------------------------------------------------------------------groups------------------------------------------------------------------------------------------------
        num_groups = (symbols + generation_size ) // generation_size
        remaining_symbols = generation_size - (num_groups * generation_size - symbols)

        groups = [list(range(i, i + generation_size)) for i in range(1, symbols + 1, generation_size)]
        if remaining_symbols > 0:
            last_group = list(range((num_groups - 1) * generation_size + 1, symbols + 1))
            if max(last_group) <= symbols: 
                groups[-1] = last_group
     
    #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        decoding_matrix_values=[] #The values needed for the decoding matrix.
        decoding_matrix_values2=[]
        systematic_index = 0  #The value that indicates how many systematic symbols were sent successfully
      
        total_symbol_counter=0  #number of the symbols(systematic and coded)
        goodput_time = 0 
       
       
        for i, group in enumerate(groups, start=1):
        

            lost_symbols=[] #copy of lost_symbols
            correct_sent_not_in_order=[] 
            print(f"Group {i}: {', '.join(map(str, group))}")
            print("=========================================")

            encoder = CustomEncoder(field, len(group), symbol_bytes)
            decoder = pyerasure.Decoder(field, len(group), symbol_bytes)
            generator = pyerasure.generator.RandomUniform(field, encoder.symbols,seed+i)

            data_in = urandom_from_random(seed, encoder.block_bytes)
            encoder.set_symbols(data_in)

           
            rate_counter=0 #counter that counts the number of uncoded symbols sent before the coded symbols.( rate_of_systematic_symbol )
   
            systematic_index = 0
            pending_list_required=True
            sent_source_symbol=0
            num_of_coded_i_need=0 #The coded symbols needed for decoding.
            num_of_lost_symbols=0 #The number of lost symbols.

            decoding_matrix_values2=[]
            for j in range(len(group)):
        
                 
                
                process_systematic_symbol(encoder, decoder, loss_probability,systematic_index,
                                          time_hashmap,lost_symbols,pending_symbols)
               
             
                goodput_time+=1
                systematic_index += 1
                total_symbol_counter += 1
                rate_counter+=1 


                #"It starts sending coded symbols when the count of the rate_counter reaches
                # the number of uncoded symbols that need to be sent before the coded ones."                                                       
                if rate_counter==rate_of_systematic_symbol:
                    counter=0  # counter that increments until it reaches 'n' (rate of coded symbol)
      
                    while counter < rate_of_coded_symbol:
                        process_coded_symbol(encoder, decoder, generator, loss_probability,
                                     time_hashmap, decoding_matrix_values, lost_symbols,pending_symbols,systematic_index,generation_size,decoding_matrix_values2)
                        
                        total_symbol_counter += 1
                        counter+=1
                        rate_counter=0
                        goodput_time+=1
                    
                    pending_list_required=True
                    
                    counter=0

                #If the count of the rate_counter does not reach the number of uncoded symbols that need to be sent before the coded ones,
                # we send additional coded symbols for protection.
                if j==len(group)-1 and  generation_size%rate_of_systematic_symbol!=0 :
                   
                    c=math.floor(generation_size/rate_of_systematic_symbol)*rate_of_coded_symbol #Coded symbols that need to be sent.
                   
                    extra_coded_symbols=math.ceil(generation_size/R -generation_size-c )
                   
                    for _ in range(extra_coded_symbols):
                        process_coded_symbol(encoder, decoder, generator, loss_probability, time_hashmap, decoding_matrix_values, lost_symbols, pending_symbols, systematic_index,generation_size,decoding_matrix_values2)
                       
                        total_symbol_counter += 1
                        goodput_time+=1
                    pending_list_required=True
                

            decoding_matrix_per_group[f"Group {i-1}"]=decoding_matrix_values2
                
            
                    
           
            if num_of_lost_symbols > num_of_coded_i_need:
                for key in lost_symbols + pending_symbols:
                    if key in time_hashmap:
                        time_hashmap[key] = [-1]     
                        

            pending_symbols=[]


        print(f"---------------------------------------------------")



        #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------       
      

        sum_of_decoding_matrix=0
        # chooses which of the two managment mechanisms to use
        if drop_gen==1:
            #Drop out of order
            total_avg_in_order_delay=0
            for key,value in time_hashmap.items():
                if value!=[-1] :
                    useful_symbol+=1
                    total_avg_in_order_delay +=value[0]
                    status[key]="decode"
                else:
                    status[key]='drop'
            sorted_status = dict(sorted(status.items()))
            print("status =", sorted_status)
        
            
            if useful_symbol==0:
                print("==============================================")
                print("Average in order delay:No useful_symbol transmitted")
                print("----------------------------------------------")
            else:
                average_in_order_delay=total_avg_in_order_delay/useful_symbol

                print("==============================================")
                print(f"Average in order delay: {average_in_order_delay} slots")
                print("----------------------------------------------")

            sum_of_decoding_matrix=sum(decoding_matrix_values)
        
            list_length = len(decoding_matrix_values)
        
       
       
            if list_length!=0:
                decoding_matrix=sum_of_decoding_matrix/list_length
                print(f"Decoding matrix size: {decoding_matrix} ")
            else:
                print(f"Decoding matrix array is empty ")
        
        else: 
            #Drop generation
            total_avg_in_order_delay = 0
      

            useful_symbol=symbols
            for i, group in enumerate(groups):
                group_status = "decode" 

                for key, value in time_hashmap.items():
                    if key in group and -1 in value:
                        group_status = "drop"
                        break

                status[f"Group {i}"] = group_status

            print(status)
           
            for i in range(len(groups)):
                if status[f"Group {i}"] == 'drop':
                    useful_symbol -= group_len[i]

            
            for i in range(len(groups)):
                if status[f"Group {i}"] != 'drop':
                    group_values = [time_hashmap[key][0] for key in groups[i] if key in time_hashmap]
                    total_avg_in_order_delay += sum(group_values)
           
            num_elements=0 
            for group, group_status in status.items():
                if group_status == 'decode':
                    sum_of_decoding_matrix += sum(decoding_matrix_per_group[group])
                    num_elements += len(decoding_matrix_per_group[group])
            
            if useful_symbol==0:
                print("==============================================")
                print("No useful_symbol transmitted")
                print("----------------------------------------------")
            else:
                average_in_order_delay=total_avg_in_order_delay/useful_symbol

                print("==============================================")
                print(f"Average in order delay: {average_in_order_delay} slots")
                print("----------------------------------------------")
           
           
           
        
       
       
            if num_elements!=0:
                decoding_matrix=sum_of_decoding_matrix/num_elements
                print(f"Decoding matrix size: {decoding_matrix} ")
            else:
                print(f"Decoding matrix array is empty ")
            
       
        #-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
       
        useful_symbols_rate=(useful_symbol/total_symbol_counter)*100
    
        goodput=useful_symbol/goodput_time
        goodput_bits=(useful_symbol*symbol_bytes*8)/goodput_time
    
       
   
        print("----------------------------------------------")
        print(f"Useful symbols : {useful_symbol} symbols")
        print("----------------------------------------------")
        print(f"Total symbols : {total_symbol_counter} symbols")
        print("----------------------------------------------")
        print(f"Rate of useful symbols : {useful_symbols_rate} %")
        print("----------------------------------------------")
        print(f"Goodput : {goodput}  symbols/slots")
        print("----------------------------------------------")
        print(f"Goodput : {goodput_bits}  bits/slots")
        print("==============================================")

        
     
       
    
        
if __name__ == "__main__":
    main(sys.argv[1:])