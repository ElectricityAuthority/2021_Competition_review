
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
import EAtools as ea
from db import DB
import os
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.mlab import griddata
import matplotlib.pyplot as plt
from matplotlib import cm
get_ipython().run_line_magic('pylab', 'inline')
con = DB(profile="millerr")  # this is the Environment database
from datetime import datetime, date, time, timedelta
path=os.getcwd()


# In[2]:


# dateBeg = '2014-01-01'
dateBeg = '2021-10-31'
dateEnd = '2021-10-31'


# #### Get generation and reserve

# In[3]:


def date_converter2(x):
    '''Convert date string in form YYYY-MM-DD to datetime object'''
    return datetime(int(x.split('-')[0]),
                    int(x.split('-')[1]),
                    int(x.split('-')[2]))

def get_generation_data(con, dateBeg=None, dateEnd=None):
    """Grab all generation data from the Data Warehouse between dateBeg and dateEnd"""
    q="""SELECT 
      tp.data_date Trading_DATE, 
      tp.Period Trading_Period,
      [ISLAND]+'I' Island,
      [pnode_name] PNode,
      [Trader_name] Trader_Id,
      [cleared_offer] FP_cleared_generation
      
      FROM [Wholesale_FP].[atomic].[Atm_Spdsolved_Trader_Periods] tp
      join [Wholesale_FP].[atomic].[Atm_Mssmkt_Traders] t on tp.data_date=t.data_date and tp.trader_id=t.trader_id
      join [DWCommon].[com].[NodeRegion] nr on left(tp.pnode_name,7)=nr.POC
      
      WHERE trade_type='ENOF'
      and tp.data_date between '%s' and '%s' """ % (dateBeg, dateEnd)
    
    df = con.query(q)
    if not isinstance(df['Trading_DATE'][0], date):
        df['Trading_DATE'] = df.Trading_DATE.map(lambda x: date_converter2(x))
    df = df.set_index(['Trading_DATE', 'Trading_Period', 'Island', 'Trader_Id',
                       'PNode']).sort_index()
    return df


# In[4]:


gen=get_generation_data(con, dateBeg,dateEnd)
genComplete=gen.reset_index(['Island','Trader_Id'],drop=True)


# In[5]:


def get_reserve_cleared(con, dateBeg=None, dateEnd=None):
    """get cleared reserve data from the Data Warehouse betweeen dateBeg and dateEnd"""
    q = """
    Select
      rc.Trading_DATE,
      rc.Trading_Period,
      rc.Island,
      rc.Reserve_class,
      rc.Trader_ID,
      rc.PNode,
      rc.Trade_type,
      rc.FP_reserve_cleared
    From
      [DWMarketdata].[com].[Fp_Reserve_cleared] rc
    Where rc.Trading_Date between '%s' and '%s' """ % (dateBeg, dateEnd)
    
    df = con.query(q)
    if not isinstance(df['Trading_DATE'][0], date):
        df['Trading_DATE'] = df.Trading_DATE.map(lambda x: date_converter2(x))
    df = df.set_index(['Trading_DATE', 'Trading_Period', 'Island',
                       'Trader_ID', 'Reserve_class', 'Trade_type', 'PNode'])
    return df.sort_index()


# In[6]:


res=get_reserve_cleared(con, dateBeg,dateEnd)
resComplete=res.reset_index(['Island','Trader_ID'],drop=True) #used later
res.index.set_names('Trader_Id', level=3, inplace=True)
resMax=res.loc[res.index.map(lambda x: x[5] in ['PLRO','TWRO'])].groupby(level=[0,1,2,3,4,6]).sum().groupby(level=[0,1,2,3,5]).max() # max of FIR and SIR


# #### Get Market Node Constaint data

# In[7]:


def get_MnCnst_data(dateBeg=None,dateEnd=None):
    """Grab Market Node Constraint data from the Data warehouse betweeen dateBeg and dateEnd"""
    q=r"""SELECT
      [DATA_DATE] Trading_DATE
      ,[constraint_name]
      ,[PERIOD] Trading_Period
      ,[upper_limit] limit
      ,[valid_upper_limit]
      FROM [Wholesale_FP].[atomic].[Atm_Mssmod_Market_Node_Constraints]
      WHERE DATA_DATE between '%s' and '%s' """ % (dateBeg, dateEnd)
    
    MnCnst = con.query(q)
    MnCnst=MnCnst[MnCnst.valid_upper_limit]
    MnCnst.drop(columns='valid_upper_limit',inplace=True)
    MnCnst['Trading_DATE'] = MnCnst.Trading_DATE.map(lambda x: date_converter2(x))
    MnCnst.set_index(['Trading_DATE','Trading_Period','constraint_name'],inplace=True)
    return MnCnst


# In[8]:


MnCnst=get_MnCnst_data(dateBeg,dateEnd)


# In[9]:


def get_MnCnstFactors_data(dateBeg=None,dateEnd=None):
    """Grab Market Node Constraint factors from the DW betweeen dateBeg and dateEnd"""
    q=r"""SELECT 
       [DATA_DATE] Trading_DATE
      ,[constraint_name]
      ,[pnode_name] PNode
      ,[trade_type] Trade_type
      ,[PERIOD] Trading_Period
      ,[factor]
      ,[factor_six]
      FROM [Wholesale_FP].[atomic].[Atm_Mssmod_Market_Node_Constraint_Weight_Factors]
      WHERE DATA_DATE between '%s' and '%s' """ % (dateBeg, dateEnd)
    
    MnCnstFactors = con.query(q)
    MnCnstFactors['Trading_DATE'] = MnCnstFactors.Trading_DATE.map(lambda x: date_converter2(x))
    MnCnstFactors=MnCnstFactors[~MnCnstFactors.constraint_name.str.contains('CTRLMIN')]
    MnCnstFactors['constr_block'] = MnCnstFactors.constraint_name.str.rsplit(pat='_', n=1).apply(lambda x: x[0])
    MnCnstFactors.set_index(['Trading_DATE','Trading_Period','constr_block','constraint_name','PNode','Trade_type'],inplace=True)
    MnCnstFactors=MnCnstFactors.unstack()
    MnCnstFactors=MnCnstFactors.reorder_levels([1,0], axis=1)
    MnCnstFactors=MnCnstFactors[['ENOF','TWRO','PLRO']]
    MnCnstFactors=MnCnstFactors.reorder_levels([1,0], axis=1)
    MnCnstFactors=MnCnstFactors.drop(columns=[('factor_six','ENOF')]).fillna(0)
    MnCnstFactors=pd.DataFrame(MnCnstFactors.stack().stack())
    temp=MnCnstFactors.index.names.copy()
    temp[-1]='Reserve_class'
    MnCnstFactors.index.names = temp
    MnCnstFactors.rename(index={'factor':'SIR','factor_six':'FIR'},inplace=True)
    MnCnstFactors.reset_index(['Trade_type','Reserve_class'],inplace=True)
    MnCnstFactors.loc[MnCnstFactors.Trade_type=='ENOF','Reserve_class']=NaN
    MnCnstFactors.set_index(['Trade_type','Reserve_class'],append=True,inplace=True)
    MnCnstFactors.rename(columns={0:'Factor'},inplace=True)
    return MnCnstFactors


# In[10]:


MnCnstFactors=get_MnCnstFactors_data(dateBeg,dateEnd)
MnCnstFactors=MnCnstFactors.join(resComplete, on=['Trading_DATE','Trading_Period','Reserve_class','Trade_type','PNode'])
MnCnstFactors=MnCnstFactors.join(genComplete, on=['Trading_DATE','Trading_Period','PNode'])
MnCnstFactors.reset_index(['Trade_type'],inplace=True)

cnstClass=MnCnstFactors.loc[(MnCnstFactors.Trade_type!='ENOF')&(MnCnstFactors.Factor==1)].groupby(level=[0,1,2,3,5]).Factor.max()
cnstClass=pd.DataFrame(cnstClass).drop(columns='Factor')

MnCnstFactorsRes=MnCnstFactors.copy()
MnCnstFactorsRes.loc[MnCnstFactorsRes.Trade_type=='ENOF','component']=    MnCnstFactorsRes.loc[MnCnstFactorsRes.Trade_type=='ENOF','Factor']*    MnCnstFactorsRes.loc[MnCnstFactorsRes.Trade_type=='ENOF','FP_cleared_generation']
MnCnstFactorsRes.loc[MnCnstFactorsRes.Trade_type!='ENOF','component']=0
MnCnstFactorsRes.drop(columns=['Factor','FP_reserve_cleared','FP_cleared_generation'],inplace=True)
MnCnstFactorsRes.set_index(['Trade_type'],append=True,inplace=True)

MnCnstFactors.loc[MnCnstFactors.Trade_type=='ENOF','component']=0
MnCnstFactors.loc[MnCnstFactors.Trade_type!='ENOF','component']=    MnCnstFactors.loc[MnCnstFactors.Trade_type!='ENOF','Factor']*    MnCnstFactors.loc[MnCnstFactors.Trade_type!='ENOF','FP_reserve_cleared']
MnCnstFactors.drop(columns=['Factor','FP_reserve_cleared','FP_cleared_generation'],inplace=True)
MnCnstFactors.set_index(['Trade_type'],append=True,inplace=True)

MnCnstRes=MnCnst.copy()
MnCnstRes=MnCnstFactorsRes.join(MnCnstRes,on=['Trading_DATE','Trading_Period','constraint_name'])

MnCnst=MnCnstFactors.join(MnCnst,on=['Trading_DATE','Trading_Period','constraint_name'])

MnCnstRemRes=MnCnstRes.groupby(level=[0,1,2,3]).agg({'component':sum, 'limit':'first'})
MnCnstRemRes['rem']=MnCnstRemRes.limit-MnCnstRemRes.component
MnCnstRemRes=cnstClass.join(MnCnstRemRes,on=['Trading_DATE','Trading_Period','constr_block','constraint_name'])
MnCnstRemRes=MnCnstRemRes.reset_index('constraint_name',drop=True)['rem']
# get the constituent nodes back
MnCnstRemRes=MnCnstFactorsRes.join(MnCnstRemRes,on=['Trading_DATE','Trading_Period','constr_block','Reserve_class'])
MnCnstRemRes=pd.DataFrame(MnCnstRemRes.groupby(level=[0,1,2,4,5]).rem.first()).reset_index(2)

MnCnstRem=MnCnst.groupby(level=[0,1,2,3]).agg({'component':sum, 'limit':'first'})
MnCnstRem['rem']=MnCnstRem.limit-MnCnstRem.component

MnCnstRem=MnCnstRem.groupby(level=[0,1,2]).rem.min()

MnCnstRem=MnCnstFactors.join(MnCnstRem,on=['Trading_DATE','Trading_Period','constr_block'],how='left')

MnCnstRem=pd.DataFrame(MnCnstRem.groupby(level=[0,1,2,4]).rem.first()).reset_index(2)


# ### Get Energy Offers

# In[11]:


def getEnergyOffers(dateBeg,dateEnd):
    islandAdjustedOfferQuery=r"""
    Select        
    Offer.Trading_DATE,
    Offer.Trading_Period
      ,map.Island+'I' Island
      ,Offer.Trader_Id
      ,Offer.Pnode as PNode
      ,Offer_Block as Offer_block
      ,Offer_Price as Offer_price
      ,Offer_Quantity as Offer_quantity
      ,Offer_Max_MW as Max_Energy
      ,Is_Wind_Offer
    From (DWMarketData.com.Fp_Offers offer
        inner join DWCommon.com.NodeRegion map on left(offer.pnode,7)=map.POC)

        left Join DWMarketData.com.FP_Offer_parameters Para
            On (Offer.DTTM_ID = Para.DTTM_ID and Offer.PNode = Para.Pnode)
    Where Offer.Trading_Date between '%s' and '%s'
        and Trade_type = 'ENOF'
        and Offer_Quantity > 0
        and (Offer_Max_MW is not null) 
    Order by Trading_DATE,Trading_Period,PNode,Offer_price,Offer_block
    """ % (dateBeg,dateEnd)

    data=con.query(islandAdjustedOfferQuery)

    if not isinstance(data['Trading_DATE'][0], date):
        data['Trading_DATE'] = data.Trading_DATE.map(lambda x: date_converter2(x))
    data = data.set_index(['Trading_DATE', 'Trading_Period', 'Island', 'Trader_Id', 'PNode'])
    
    return data.sort_index()


# In[12]:


EnOfd = getEnergyOffers(dateBeg,dateEnd)


# #### join dataframes

# In[13]:


EnOfd=EnOfd.merge(gen, how='left', on=['Trading_DATE', 'Trading_Period', 'Island', 'Trader_Id', 'PNode']).merge(
                    resMax, how='left', on=['Trading_DATE', 'Trading_Period', 'Island', 'Trader_Id', 'PNode']).fillna(0)


# In[14]:


# Limit wind offers to actual generation
EnOfd.loc[EnOfd['Is_Wind_Offer']==1,'Max_Energy']=EnOfd.loc[EnOfd['Is_Wind_Offer']==1,'FP_cleared_generation']
EnOfd['Max_Energy']=EnOfd.Max_Energy-EnOfd.FP_reserve_cleared

#join has a bug that produces an error so use merge instead
EnOfd.reset_index(['Island','Trader_Id'],inplace=True)
EnOfd=EnOfd.merge(MnCnstRem, how='left', left_index=True, right_index=True)
EnOfd.set_index(['Island','Trader_Id'],inplace=True,append=True)
EnOfd=EnOfd.reorder_levels([0,1,3,4,2])
EnOfd.constr_block.fillna('None',inplace=True)
EnOfd.set_index(['constr_block','Offer_price'],append=True,inplace=True)
EnOfd.sort_index(level=[0,1,2,5,6], ascending=True, inplace=True) #price sort each block
EnOfd.sort_index(level=[0,1,2,4,6], ascending=True, inplace=True) #price sort each node


# #### Apply MWMAX

# In[15]:


energy = []
quantity = []
lastDate=''
lastTp=''
lastNode=''  

EnOfd.reset_index(inplace=True)


# In[16]:


for index,row in EnOfd.T.iteritems():  
    #Check if date, trading period and Pnode is same as last one. If true, calculate the remaining value of max_energy.
#     if row['Trading_DATE'] != lastDate:
#         print(row['Trading_DATE'])
    if row['Trading_DATE'] != lastDate or row['Trading_Period'] != lastTp or row['PNode'] != lastNode:
        max_energy = row['Max_Energy']    #chg to max_energy     
    else:
        max_energy = max_energy - new_quantity   #max_energy remaining up to this point
    if max_energy > row['Offer_quantity']:
        new_quantity = row['Offer_quantity']
    else:
        new_quantity = max_energy       

    lastDate = row['Trading_DATE']
    lastTp = row['Trading_Period']
    lastNode = row['PNode']    
    energy.append(max_energy)
    quantity.append(new_quantity)
EnOfd['Quantity_Calc_Temp']=quantity #Adjusted for MWMAX


# #### Apply Market Node Constraints

# In[17]:


energy = []
quantity = []
lastDate=''
lastTp=''
lastBlk=''  

EnOfd.set_index(['Trading_DATE','Trading_Period','Island','Trader_Id','PNode','constr_block','Offer_price'], inplace=True)
EnOfd.sort_index(level=[0,1,2,5,6], ascending=True, inplace=True) #price sort each block
EnOfd.reset_index(inplace=True)


# In[18]:


for index,row in EnOfd.T.iteritems():  
#     if row['Trading_DATE'] != lastDate:
#         print(row['Trading_DATE'])
    if row['constr_block']=='None':
        max_energy = row['rem']
        new_quantity = row['Quantity_Calc_Temp']
    else:
        #Check if date, trading period and Blk is same as last one. If true, calculate the remaining value of max_energy.
        if row['Trading_DATE'] != lastDate or row['Trading_Period'] != lastTp or row['constr_block'] != lastBlk:
            max_energy = row['rem']    #chg to max_energy     
        else:
            max_energy = max_energy - new_quantity   #max_energy remaining up to this point
        if max_energy > row['Quantity_Calc_Temp']:
            new_quantity = row['Quantity_Calc_Temp']
        else:
            new_quantity = max_energy       

    lastDate = row['Trading_DATE']
    lastTp = row['Trading_Period']
    lastBlk = row['constr_block']    
    energy.append(max_energy)
    quantity.append(new_quantity)
EnOfd['Quantity_Calc']=quantity #Adjusted for Market Node Constraints

EnOfd.to_parquet('EffectiveEnergyOffers.parquet')

