'''Class JuMEG_Epocher_Events

Class to extract event/epoch information and save to hdf5
extract mne-events per condition, save to HDF5 file
----------------------------------------------------------------
Author:
--------
         Frank Boers     <f.boers@fz-juelich.de>


Updates:
----------------------------------------------------------------
update: 19.06.2018          
complete new, support for IOD and eyetracking events
----------------------------------------------------------------
Example:
--------

#--- example via obj:
from jumeg.epocher.jumeg_epocher        import jumeg_epocher
from jumeg.epocher.jumeg_epocher_epochs import JuMEG_Epocher_Epochs
from jumeg.jumeg_base                   import jumeg_base as jb

#--
jumeg_epocher.template_path ='.' 
jumeg_epocher.verbose       = verbose
#---
jumeg_epocher_epochs        = JuMEG_Epocher_Epochs()
#---
fname          = test.fif
raw            = None
condition_list = ["Cond1","Condi2"]


#--- events: finding events, store into pandas dataframe ansd save as hdf5
#--- parameter for apply_events_to_hdf

evt_param = { "condition_list":condition_list,
              "template_path": template_path, 
              "template_name": template_name,
              "verbose"      : verbose
            }
              
(_,raw,epocher_hdf_fname) = jumeg_epocher.apply_events(fname,raw=raw,**evt_param)

   
#--- epochs
ep_param={
          "condition_list": condition_list,
          "template_path" : template_path, 
          "template_name" : template_name,
          "verbose"       : verbose,
          "parameter":{
                       "event_extention": ".eve",
                       "save_condition":{"events":True,"epochs":True,"evoked":True}
                      }}  
#--- 
print "---> EPOCHER Epochs"
print "  -> File            : "+ fname
print "  -> Epocher Template: "+ template_name+"\n"   
jumeg_epocher.apply_epochs(fname=fname,raw=raw,**ep_param)



'''
import sys
import numpy as np
import pandas as pd

import mne
from jumeg.jumeg_base                import jumeg_base,JuMEG_Base_Basic,JuMEG_Base_PickChannels
from jumeg.epocher.jumeg_epocher_hdf import JuMEG_Epocher_HDF

__version__="2018.06.19.001"


class JuMEG_Epocher_Channel_Baseline(object):
    """ 
    base class for baseline dict definitions  & properties
    "baseline" :{"method":"avg","type_input":"iod_onset","baseline": [null,0]},
    """
    def __init__(self,parameter=None,label="baseline"):
        super(JuMEG_Epocher_Channel_Baseline,self).__init__()
        self._param = parameter   
        self._label = label
   #---   
    def _get_param(self,key=None):
        try:
            if key in self._param[self._label]:
               return self._param[self._label][key] 
        except:
            pass
        return None       
   #---    
    def _set_param(self,key=None,val=None):
        self._param[self._label][key] = val      
        
   #---baseline type
    @property
    def method(self): return self._get_param("method")
    @method.setter
    def method(self,v): self._set_param("method",v)
   #---baseline type
    @property
    def type_input(self): return self._get_param("type_input")  
    @type_input.setter
    def type_put(self,v): self._set_param("type_input",v)
   #---baseline
    @property
    def baseline(self): return self._get_param("baseline")  
    @baseline.setter
    def baseline(self,v): self._set_param("baseline",v)
  #---baseline
    @property
    def onset(self):
        if type( self._get_param("baseline") ) is list: return self.baseline[0]  
    
  #---baseline
    @property
    def offset(self):
        if type( self._get_param("baseline") ) is list: return self.baseline[1]  
   

class JuMEG_Epocher_Basic(JuMEG_Base_Basic):
    """ 
    base class for definitions  & properties
    
    """
    
    def __init__(self):
        super(JuMEG_Epocher_Basic,self).__init__()
        self._rt_type_list             = ['MISSED', 'TOEARLY', 'WRONG', 'HIT']
        self._data_frame_stimulus_cols = ['id','onset','offset']
        self._data_frame_response_cols = ['rt_type','rt','rt_id','rt_onset','rt_offset','rt_index','rt_counts','bads','selected','weighted_selected']
        
        self._stat_postfix = '-epocher-stats.csv'
        self._idx_bad      = -1
        self.version       = __version__
        
#---
    @property
    def idx_bad(self): return self._idx_bad
#---
    @property
    def data_frame_stimulus_cols(self): return self._data_frame_stimulus_cols
    @data_frame_stimulus_cols.setter
    def data_frame_stimulus_cols(self,v): self._data_frame_stimulus_cols = v   
#---
    @property
    def data_frame_response_cols  (self): return self._data_frame_response_cols
    @data_frame_response_cols.setter
    def data_frame_response_cols(self,v): self._data_frame_response_cols = v
    
#--- rt_type list: 'MISSED', 'TOEARLY', 'WRONG', 'HIT'
    @property
    def rt_type_list(self): return self._rt_type_list
    
#--- rt type index: 'MISSED', 'TOEARLY', 'WRONG', 'HIT'
    def rt_type_as_index(self,s):
        return self._rt_type_list.index( s.upper() )
    
    @property
    def idx_missed(self):  return self._rt_type_list.index( 'MISSED')
    @property
    def idx_toearly(self): return self._rt_type_list.index( 'TOEARLY')
    @property
    def idx_wrong(self):   return self._rt_type_list.index( 'WRONG')
    @property
    def idx_hit(self):     return self._rt_type_list.index( 'HIT')
  #--- 
    @property
    def data_frame_stimulus_cols(self): return self._data_frame_stimulus_cols
    @data_frame_stimulus_cols.setter
    def data_frame_stimulus_cols(self,v): self._data_frame_stimulus_cols = v
  #---
    @property
    def data_frame_response_cols(self): return self._data_frame_response_cols
    @data_frame_response_cols.setter
    def data_frame_response_cols(self,v): self._data_frame_response_cols = v 
  #--- events stat file (output as csv)
    @property
    def stat_postfix(self):return self._stat_postfix
    @stat_postfix.setter
    def stat_postfix(self, v):   self._stat_postfix = v  


class JuMEG_Epocher_Events_Channel_Base(object): 
    """ base class to handel epocher template channel parameter
    
    Parameter:
    ----------
     label    : first-level key in dictionary <None>
     parameter: epocher template parameter as dictionary <None>
    
    Example:
    --------
     iod_parameter= {"marker"  :{"channel":"StimImageOnset","type_input":"img_onset","prefix":"img"},
                     "response":{"matching":true,"channel":"IOD","type_input":"iod_onset","prefix":"iod"}
                     }  
    
     response  = JuMEG_Epocher_Events_Channel_Base(label="response",parameter= iod_parameter])
     print respone.channel 
     >> IOD
        
    """
    def __init__(self,label=None,parameter=None):
        self.label = label
        self._param = parameter       
                    
#---   
    def get_channel_parameter(self,key=None,prefix=None):
        try:
            if prefix:
               k = prefix+'_'+key 
               return self._param[self.label][k] 
            else:  
               return self._param[self.label][key] 
        except:
            pass
        return None
        #return self._param
#---    
    def set_channel_parameter(self,key=None,val=None,prefix=None):
        if key:
           if prefix:
              self._param[self.label][prefix+'_'+key] = val
           else:          
              self._param[self.label][key] = val  
#---
    @property
    def matching(self):   return self.get_channel_parameter(key="matching")  
    @matching.setter
    def matching(self,v): self.get_channel_parameter(key="matching",val=v)
#--- 
    @property
    def matching_type(self):   return self.get_channel_parameter(key="matching_type")  
    @matching_type.setter
    def matching_type(self,v): self.get_channel_parameter(key="matching_type",val=v)
#--- 
    @property
    def channel(self):   return self.get_channel_parameter(key="channel")  
    @channel.setter
    def channel(self,v): self.set_channel_parameter(key="channel",val=v)
#--- 
    @property
    def prefix(self):   return self.get_channel_parameter(key="prefix")  
    @prefix.setter
    def prefix(self,v): self.set_channel_parameter(key="prefix",val=v)       
#--- 
    @property
    def type_input(self):   return self.get_channel_parameter(key="type_input")  
    @type_input.setter
    def type_input(self,v): self.set_channel_parameter(key="type_input",val=v)
#--- 
    @property
    def type_offset(self):   return self.get_channel_parameter(key="type_offset")  
    @type_offset.setter
    def type_offset(self,v): self.set_channel_parameter(key="type_offset",val=v)
#--- 
    @property
    def type_output(self):   return self.get_channel_parameter(key="type_output")  
    @type_output.setter
    def type_output(self,v): self.set_channel_parameter(key="type_output",val=v)

#---type_result: "hit","wrong","missed"
    @property
    def type_result(self):   return self.get_channel_parameter(key="type_result")  
    @type_result.setter
    def type_result(self,v): self.set_channel_parameter(key="type_result",val=v)
#--- 
    @property
    def channel_parameter(self): return self._param[self.channel]
#--- 
    @property
    def parameter(self): return self._param
    @parameter.setter
    def parameter(self,v): self._param = v    
#--- 
    @property
    def get_value_with_prefix(self,v): return self.get_channel_parameter(self,key=v,prefix=self.prefix)
#--- 
    def get_parameter(self,k): return self._param[k]
#--- 
    def set_parameter(self,k,v): self._param[k]=v 
#--- 
    @property
    def time_pre(self):   return self.get_parameter("time_pre")  
    @time_pre.setter
    def time_pre(self,v): self.set_parameter("time_pre",v)       
#--- 
    @property
    def time_post(self):   return self.get_parameter("time_post")  
    @time_post.setter
    def time_post(self,v): self.set_parameter("time_post",v) 

      
class JuMEG_Epocher_Events_Channel_IOD(object):
    """class to handel epocher template IOD parameter
    
    Parameter:
    ----------
     label    : first-level key in dictionary <iod>
     parameter: epocher template parameter as dictionary <None>
    
    Return:
    --------     
     None
    
    Example:
    --------
    input json dictonary
     parameter={
    "default":{ 
       "Stim":{ "events":{"stim_channel":"STI 014","output":"onset","consecutive":true,"min_duration":0.0005,"shortest_event":1,"mask":0},
                "event_id":84,"and_mask":255,"system_delay_ms":0.0,"early_ids_to_ignore":null},                                                
       "IOD":{ "events":{ "stim_channel":"STI 013","output":"onset","consecutive":true,"min_duration":0.0005,"shortest_event":1,"mask":0},
               "and_mask":128,"window":[0.0,0.2],"counts":"first","system_delay_ms":0.0,"early_ids_to_ignore":null,"event_id":128,"and_mask":255}
        },    
       
       "cond1":{
               "postfix":"cond1", 
               "info"   :" my comments",
               "iod"    :{"marker"  :{"channel":"StimImageOnset","type_input":"img_onset","prefix":"img"},
                          "response":{"matching":true,"channel":"IOD","type_input":"iod_onset","prefix":"iod"}},  
              "StimImageOnset" : {"event_id":94},
              "IOD"            : {"event_id":128}
             }
       }
               
     iod  = JuMEG_Epocher_Events_Channel_IOD(label="response",parameter= parameter["condi1"])
     print iod.response.channel 
     >> IOD
    
    """
    
    def __init__(self,label="iod",parameter=None):
        #super(JuMEG_Epocher_Events_Channel_IOD,self).__init__(label="iod",meter=None)
        self._info     = None
        self.label     = label
        self._param    = parameter
        self.response  = JuMEG_Epocher_Events_Channel_Base(label="response",parameter=parameter["iod"])
        self.marker    = JuMEG_Epocher_Events_Channel_Base(label="marker",  parameter=parameter["iod"])
#---
    @property
    def iod_matching(self):   return self.response.matching  
    @iod_matching.setter
    def iod_matching(self,v): self.response.matching = v        
#--- 
    @property
    def info(self):   return self._info
    @info.setter
    def info(self,v): self._info = v
#--- 
    @property
    def parameter(self): return self._param
    @parameter.setter
    def parameter(self,v):
        self._param = v
        self.response.parameter = v["iod"]
        self.marker.parameter   = v["iod"]
#--- 
    @property
    def response_channel_parameter(self): return self._param[self.response.channel]
#---    
    @property
    def marker_channel_parameter(self):   return self._param[self.marker.channel]
   
 
class JuMEG_Epocher_Events_Channel(JuMEG_Epocher_Events_Channel_Base):
    '''
    class for marker and response channel
            
    ''' 
    def __init__(self,label=None,parameter=None):
        super(JuMEG_Epocher_Events_Channel,self).__init__(label=label,parameter=parameter)
        self._info = None
         
#--- 
    @property
    def info(self):   return self._info
    @info.setter
    def info(self,v): self._info = v  
#---
    @property
    def stim_channel(self): return self._param[ self.channel ]["events"]["stim_channel"]      
    
    @property
    def stim_output(self): return self._param[ self.channel ]["events"]["output"]      
  
    
#---         
class JuMEG_Epocher_ResponseMatching(JuMEG_Epocher_Basic):
    """ 
    CLS to do response matching
    for help refer to JuMEG_Epocher_ResponseMatching.apply() function
    
    
    """
   #---
    def __init__(self,raw=None,stim_df=None,stim_param=None,stim_type_input="onset",stim_prefix="stim",
                 resp_df=None,resp_param=None,resp_type_input="onset",resp_type_offset="offset",resp_prefix="resp",verbose=False):
                
        super(JuMEG_Epocher_ResponseMatching, self).__init__()
        #self.column_name_list_update = ['rt_type','rt_id','rt_onset','rt_offset','rt_index','rt_counts']
        self.column_name_list_update = ['div','type','index','counts']
        self.column_name_list_extend = ['bads','selected','weighted_selected']
        self.raw              = raw
        self.verbose          = verbose
        self.stim_df          = stim_df       
        self.stim_param       = stim_param       
        self.stim_type_input  = stim_type_input       
        self.stim_prefix      = stim_prefix
        
      #---  
        self.resp_df          = resp_df       
        self.resp_param       = resp_param       
        self.resp_type_input  = resp_type_input 
        self.resp_type_offset = resp_type_offset 
        self.resp_prefix      = resp_prefix
      #---
        self.DataFrame  = None
   #---      
    @property
    def div_column(self): return self.resp_prefix+"-div"
    
    
    def reset_dataframe(self,max_rows):
        """
         reset output pandas dataframe
         add stimulus,response data frame columns and extend with prefix
         init with zeros x MAXROWS
         
         Parameters
         ----------
           max_rows: number of dataframe rows 
         
         Returns
         ------- 
           dataframe[ zeros x MaxRows ]
        """
        col=[]
        col+= self.stim_df.columns.tolist()
        col+= self.resp_df.columns.tolist()
        
        for key in self.column_name_list_update:
            
            if self.resp_prefix:
               k = self.resp_prefix +'_'+ key
            else: k = key
            
            if k not in col:
               col.append( k )
           
        for k in self.column_name_list_extend:
            if k not in col:
               col.append(k)
        
        return pd.DataFrame(0,index=range(max_rows),columns=col)
        
        
    def update(self,raw=None,stim_df=None,stim_param=None,stim_type_input=None,stim_prefix=None,resp_df=None,
               resp_param=None,resp_type_input=None,resp_type_offset=None,resp_prefix=None,verbose=False):
        """ update CLS parameter
       
        Parameters
        ----------
        raw              : raw obj [None]
                           used to calc time-window-range in TSLs
        stim_df          : pandas.DataFrame [None]
                           stimulus channel data frame 
        stim_param       : dict() [None]
                           stimulus parameter from template
        stim_type_input  : string ["onset"]
                           data frame column name to process as stimulus input                   
        stim_prefix      : string ["iod"]
                           stimulus column name prefix e.g. to distinguish between different "onset" columns
        resp_df          : pandas.DataFrame [None]
                           response channel data frame                   
        resp_param       : dict() [None]
                           response parameter from template                     
        resp_type_input  : string ["onset"]
                           data frame column name to process as response input 
        resp_prefix      : string ["iod"]
                           response column name prefix e.g. to distinguish between different "onset" columns                   
        
        verbose          : bool [False]
                           printing information debug
        
        """
        if raw             : self.raw             = raw
        if stim_param      : self.stim_param      = stim_param
        if stim_type_input : self.stim_type_input = stim_type_input
        if stim_prefix     : self.stim_prefix     = stim_prefix
        if resp_param      : self.resp_param      = resp_param
        if resp_type_input : self.resp_type_input = resp_type_input
        if resp_type_offset: self.resp_type_offset= resp_type_offset 
        if resp_prefix     : self.resp_prefix     = resp_prefix
        if verbose         : self.verbose         = verbose
        
        if isinstance(stim_df, pd.DataFrame):
           self.stim_df = stim_df 
        if isinstance(resp_df, pd.DataFrame):
           self.resp_df = resp_df     
        self.DataFrame  = None
        
        
        if not self.resp_type_offset:
           self.resp_type_offset = self.resp_type_inputJuMEG_Base_PickChannels
           
    def _ck_errors(self):
        """ checking for errors
        Returns:
        --------
         False if error
         
        """
      #--- ck errors
        err_msg =[] 
        
        if (self.raw is None):
           err_msg.append("ERROR no RAW obj. provided") 
        if (self.stim_df is None):
           err_msg.append("ERROR no Stimulus-Data-Frame obj. provided")
        if (self.stim_param is None):
           err_msg.append("ERROR no stimulus parameter obj. provided")
        if (self.stim_type_input is None):
           err_msg.append("ERROR no stimulus type input provided")
      
        if (self.resp_df is None):
           err_msg.append("ERROR no Response-Data-Frame obj. provided")
        
        if (self.resp_param is None):
           err_msg.append("ERROR no response parameter obj. provided")
        if (self.resp_type_input is None):
           err_msg.append("ERROR no response type input provided")
     
        if err_msg :
           self.pp(err_msg,head="JuMEG Epocher Response Matching ERROR check")
           return False 
       
        return True      
        
    def calc_max_rows(self,tsl0=None,tsl1=None,resp_event_id=None,early_ids_to_ignore=None):
        """
        counting the necessary number of rows for dataframe
        
        Parameter
        ---------
         tsl0                : response window start in tsls <None>
         tsl1                : response window end   in tsls <None>
         resp_event_id       : response event ids            <None>
         early_ids_to_ignore : ignore this response ids if there are to early pressed <None>
        
        Returns
        -------
         number of rows to setup the dataframe
        """
        max_rows = 0
       #--- get rt important part of respose df
        resp_tsls = self.resp_df[ self.resp_type_input ]
          
        for idx in self.stim_df.index :
           # st_tsl_onset   = self.stim_df[ self.stim_type_input ][idx]
            st_window_tsl0 = self.stim_df[ self.stim_type_input ][idx] + tsl0
            st_window_tsl1 = self.stim_df[ self.stim_type_input ][idx] + tsl1
           
            if (st_window_tsl0 < 0) or (st_window_tsl1 < 0) : continue
      
           #--- ck for toearly responses  
            if tsl0 > 0:
               resp_index = self.find_toearly(tsl1=tsl0,early_ids_to_ignore=early_ids_to_ignore)
               if isinstance(resp_index, np.ndarray):
                  max_rows+=1
                  continue
      
          #--- find index of responses from window-start till end of res_event_type array [e.g. onset / offset]
            resp_in_index = self.resp_df[ ( st_window_tsl0 <= resp_tsls ) & ( resp_tsls <= st_window_tsl1 ) ].index

          #--- MISSED response
            if resp_in_index.empty: 
               max_rows+=1
               continue
          
          #---count == all
          #--- no response count limit e.g. eye-tracking saccards
          #--- count defined resp ids ignore others
            if self.resp_param['counts'] == 'all':
             #--- get True/False index  
               idx_isin_true = np.where( self.resp_df[self.resp_prefix + "_id"][ resp_in_index ].isin( resp_event_id ) )[0]
               max_rows+=idx_isin_true.size
           #--- ck if first resp is True/False  e.g. IOD matching
            elif self.resp_param['counts'] == 'first':
                 max_rows+=1
                  
           #--- ck for response count limit
            elif self.resp_param['counts']: 
           #--- found responses are <= allowed resp counts
                 max_rows+=resp_in_index.size
            else:
            #--- Wrong: found response counts > counts  
                 max_rows+=resp_in_index.size
               
        return max_rows
    
    
   #---   
    def print_info(self,raw,text='Info'):
        """ print info
         Parameter
         ---------
          raw : raw obj <None>
          text: "head info text"
        
         Return
         --------
         prints statistic from column <response-prefix> -div
         e.g. prints differences in tsls between stimulus and IOD onset
         
        """
        self.pp( self.DataFrame,head=" --> Response Matching " )
        ddiv    = self.DataFrame[ self.resp_prefix + "_div" ] 
        n_zeros = ( ddiv == 0 ).sum()
        tsldiv  =  abs( ddiv.replace(0,np.NaN) )
           
        dmean  = tsldiv.mean()
        dstd   = tsldiv.std()
        dmin   = tsldiv.min()
        dmax   = tsldiv.max()  
        
        if not np.isnan(dmean):   
           tdmean = raw.times[ int(dmean)]
           tdstd  = raw.times[ int(dstd )]
           tdmin  = raw.times[ int(dmin )]
           tdmax  = raw.times[ int(dmax )]
        else:
           tdmean,tdstd,tdmin,tdmax = 0,0,0,0
        
        
        print" --> "+ text +" time difference [ms]"
        print"  -> bad epochs count : {:d}".format(n_zeros)
        print"  -> mean [ s ]: {:3.3f}  std: {:3.3f} max: {:3.3f} min: {:3.3f}".format(tdmean,tdstd,tdmin,tdmax)
        print"  -> mean [tsl]: {:3.3f}  std: {:3.3f} max: {:3.3f} min: {:3.3f}".format(dmean,dstd,dmin,dmax)
        self.line()   
   
   #---   
    def _set_stim_df_resp(self,df,stim_idx=None,df_idx=None,resp_idx=None,resp_type=0,counts=0):
        """set dataframe row
         Parameter
         ---------
          df       : dataframe
          stim_idx : index <None>
          df_idx   : <None>
          resp_idx : <None>
          resp_type: <0>
          counts   : <0>    
         
         Return
         --------
          dataframe
          
        """
        for col in self.stim_df.columns:
            df[col][df_idx] = self.stim_df[col][stim_idx]
       
        if self.is_number( resp_idx ):
           for col in self.resp_df.columns:
               df[col][df_idx] = self.resp_df[col][resp_idx]
           df[self.resp_prefix +'_index'][df_idx] = resp_idx
        else:
           for col in self.resp_df.columns:
               df[col][df_idx] = 0
           df[self.resp_prefix +'_index'][df_idx] = 0
           
        df[self.resp_prefix +'_type'][df_idx]    = resp_type
        df[self.resp_prefix + "_counts"][df_idx] = counts
        df[self.resp_prefix + "_div"][df_idx]    = df[ self.resp_type_input ][df_idx]- df[ self.stim_type_input ][df_idx]
      
        return df

    def _set_hit(self,df,stim_idx=None,df_idx=None,resp_idx=None):
        """ set dataframe row for correct responses
         Parameter
         ---------
          df       : dataframe
          stim_idx : index <None>
          df_idx   : <None>
          resp_idx : <None>
          resp_type: <0>
          counts   : <0>    
         
         Return
         --------
          dataframe
        """ 
        cnt = 0
        for ridx in resp_idx: 
            df_idx += 1
            cnt    += 1
            self._set_stim_df_resp(df,stim_idx=stim_idx,df_idx=df_idx,resp_idx=ridx,resp_type=self.idx_hit,counts=cnt) 
        return df_idx    
    
    def _set_wrong(self,df,stim_idx=None,df_idx=None,resp_idx=None):
        """ set dataframe row for wrong responses
         Parameter
         ---------
          df       : dataframe
          stim_idx : index <None>
          df_idx   : <None>
          resp_idx : <None>
          resp_type: <0>
          counts   : <0>    
         
         Return
         --------
          dataframe
        """  
        cnt = 0
        for ridx in resp_idx: 
            df_idx += 1
            cnt    += 1
            self._set_stim_df_resp(df,stim_idx=stim_idx,df_idx=df_idx,resp_idx=ridx,resp_type=self.idx_wrong,counts=cnt) 
        return df_idx    
  
  #---
    def find_toearly(self,tsl0=0,tsl1=None,early_ids_to_ignore=None):
        """ look for part of to early response  in dataframe
        Parameters
        ----------
         tsl0 :  start tsl range <None>
         tsl1 :  end   tsl range <None>
         early_ids_to_ignores: ignore this ids in window  tsl-onset <= tsl < tsl0  <None>
             
        Return
        ------
        array Int64Index([ number of toearly responses ], dtype='int64')
        """
        if self.resp_param["early_ids_to_ignore"] == 'all':
           return 
        
        early_idx = self.resp_df[ ( tsl0 <= self.resp_df[ self.resp_type_input ] ) & ( self.resp_df[ self.resp_type_input ] < tsl1 ) ].index
     
      #---  ck for button is pressed  released 
        if self.resp_type_input != self.resp_type_offset:
           early_idx_off = self.resp_df[ ( tsl0 <= self.resp_df[ self.resp_type_offset] ) & ( self.resp_df[ self.resp_type_offset ] < tsl1 ) ].index
           early_idx     = np.unique( np.concatenate((early_idx,early_idx_off), axis=0) )
    
        #print"---Toearly"
        #print tsl0
        #print tsl1
        #print early_idx 
        #print self.resp_df[ ( tsl0 <= self.resp_df[ self.resp_type_input ] ) & ( self.resp_df[ self.resp_type_offset ] < tsl1 ) ]
           
        if early_idx.any():
               
           if self.resp_param['early_ids_to_ignore']:
              if early_ids_to_ignore.any():
                 evt_found = self.resp_df[self.resp_prefix + "_id"][ early_idx ].isin( early_ids_to_ignore ) # true or false
                 
                 if evt_found.all():
                    return
                 found = np.where( evt_found == False )[0]
                 return found
              
           else:
                return early_idx
            
        return None          
    
  #--- 
    def apply(self,*kargs, **kwargs):   
        """ 
        apply response matching
              
        matching correct responses with respect to <stimulus channel> <output type> (onset,offset)
    
        Parameters
        ----------
         raw              : raw obj [None]
                            used to calc time-window-range in TSLs
         stim_df          : pandas.DataFrame [None]
                            stimulus channel data frame 
         stim_param       : dict() [None]
                            stimulus parameter from template
         stim_type_input  : string ["onset"]
                            data frame column name to process as stimulus input                   
         stim_prefix      : string ["iod"]
                            stimulus column name prefix e.g. to distinguish between different "onset" columns
         resp_df          : pandas.DataFrame [None]
                            response channel data frame                   
         resp_param       : dict() [None]
                            response parameter from template                     
         resp_type_input  : string ["onset"]
                            data frame column name to process as response input 
         resp_prefix      : string ["iod"]
                            response column name prefix e.g. to distinguish between different "onset" columns                   
        
         verbose          : bool [False]
                            printing information debug
        Returns
        -------    
         pandas.DataFrame 
     
        """
        self.update(*kargs,**kwargs)
        if not self._ck_errors():
           return
           
       #--- ck RT window range
        if ( self.resp_param['window'][0] >= self.resp_param['window'][1] ):
           print" --> ERROR in <apply_response_matching>"
           print("ERROR in self.parameter response windows")
           return
        
        (r_window_tsl_start, r_window_tsl_end ) = self.raw.time_as_index( self.resp_param['window'] );
        
       #--- get respose code -> event_id [int or string] as np array
        resp_event_id = jumeg_base.str_range_to_numpy( self.resp_param['event_id'] )


       #--- ck if any toearly-id is defined, returns None if not
        if self.resp_param["early_ids_to_ignore"] != 'all':
           early_ids_to_ignore = jumeg_base.str_range_to_numpy( self.resp_param['early_ids_to_ignore'] )
        else:
           early_ids_to_ignore=None 
      
       #--- loop for all stim events
        ridx = 0
       #--- get rt important part of respose df
        resp_tsls = self.resp_df[ self.resp_type_input ]
        
        max_rows = self.calc_max_rows(tsl0=r_window_tsl_start,tsl1=r_window_tsl_end,resp_event_id=resp_event_id,early_ids_to_ignore=early_ids_to_ignore)
        df = self.reset_dataframe(max_rows)
        
        df_idx = -1
        
        for idx in self.stim_df.index :
            st_window_tsl0 = self.stim_df[ self.stim_type_input ][idx] + r_window_tsl_start
            st_window_tsl1 = self.stim_df[ self.stim_type_input ][idx] + r_window_tsl_end
            
            if (st_window_tsl0 < 0) or (st_window_tsl1 < 0) : continue
           
         #--- to-early responses  e.g. response winfow[0.01,1,0] =>  =>  0<= toearly window < 0.01
            if r_window_tsl_start > 0:
               resp_index = self.find_toearly(tsl1=st_window_tsl0,early_ids_to_ignore=early_ids_to_ignore)
               if isinstance(resp_index, np.ndarray):
                  df_idx += 1
                  self._set_stim_df_resp(df,stim_idx=idx,df_idx=df_idx,resp_idx=ridx,resp_type=self.idx_toearly,counts=resp_index.size )
                  continue

          #--- find index of responses from window-start till end of res_event_type array [e.g. onset / offset]
            resp_in_index = self.resp_df[ ( st_window_tsl0 <= resp_tsls ) & ( resp_tsls <= st_window_tsl1) ].index

            
          #--- MISSED response
            if resp_in_index.empty:
               df_idx += 1
               self._set_stim_df_resp(df,stim_idx=idx,df_idx=df_idx,resp_idx=None,resp_type=self.idx_missed,counts=0 )
               continue
           
           #---count == all
           #--- no response count limit e.g. eye-tracking saccards
           #--- count defined resp ids ignore others
            if self.resp_param['counts'] == 'all':
             #--- get True/False index  
               idx_isin_true = np.where( self.resp_df[self.resp_prefix + "_id"][ resp_in_index ].isin( resp_event_id ) )[0]
             #--- get index of True Hits   
               resp_in_idx_hits = resp_in_index[idx_isin_true]
               if resp_in_idx_hits.any():
                  df_idx = self._set_hit(df,stim_idx=idx,df_idx=df_idx,resp_idx=resp_in_idx_hits)  
          
           #--- ck if first resp is True/False  e.g. IOD matching
            elif self.resp_param['counts'] == 'first':
               if ( self.resp_df[self.resp_prefix + "_id"][ resp_in_index[0] ] in resp_event_id ):
                  df_idx = self._set_hit(df,stim_idx=idx,df_idx=df_idx,resp_idx=[ resp_in_index[0] ] )   
               else:
                  df_idx = self._set_wrong(df,stim_idx=idx,df_idx=df_idx,resp_idx=[resp_in_index[0]] )  
        
           #--- ck for response count limit
            elif self.resp_param['counts']: 
                #--- found responses are <= allowed resp counts
                 if ( resp_in_index.size <= self.resp_param['counts'] ):
                #--- HITS: all responses are in response event id
                    if np.all( self.resp_df[self.resp_prefix + "_id"][ resp_in_index ].isin( resp_event_id ) ) :
                       df_idx = self._set_hit(df,stim_idx=idx,df_idx=df_idx,resp_idx=resp_in_index ) 
                    else:
                #--- Wrong: not all responses are in response event id =>found responses are > allowed resp counts
                       df_idx = self._set_wrong(df,stim_idx=idx,df_idx=df_idx,resp_idx=resp_in_index)  
            #--- Wrong: found response counts > counts      
                 else:
                   df_idx = self._set_wrong(df,stim_idx=idx,df_idx=df_idx,resp_idx=resp_in_index)  
           
        
        self.DataFrame = df
       #char = sys.stdin.read(1)
        return df
  

class JuMEG_Epocher_Events(JuMEG_Epocher_HDF,JuMEG_Epocher_Basic):
    ''' 
    Main class to find events
    -> reading epocher event template file
    -> for each condition find events using mne.find_events function
    -> looking for IOD and response matching
    -> store results into pandas dataframes
    -> save as hdf5 for later to generate epochs,averages
   
    Example
    --------
    from jumeg.epocher.jumeg_epocher import jumeg_epocher
    from jumeg.epocher.jumeg_epocher_epochs import JuMEG_Epocher_Epochs
    jumeg_epocher_epochs = JuMEG_Epocher_Epochs()
    
    jumeg_epocher.template_path = '.'
    condition_list = ['test01','test02']
    fname          = "./test01.fif"
        
    param = { "condition_list":condition_list,
              "do_run": True,
              "template_name": "TEST01",
              "save": True
             }
              
    (_,raw,epocher_hdf_fname) = jumeg_epocher.apply_events_to_hdf(fname,**param)

    '''
#---
    def __init__(self):

        super(JuMEG_Epocher_Events, self).__init__()
      
        self.parameter         = None
        self.stimulus          = None
        self.response          = None
        self.iod               = None
        self.event_data_parameter={"events":{
                                             "stim_channel"   : "STI 014",
                                             "output"         : "onset",
                                             "consecutive"    : True,
                                             "min_duration"   : 0.0001,
                                             "shortest_event" : 1,
                                             "mask"           : 0
                                            },
                                    "event_id" : None,        
                                    "and_mask" : None,
                                    "system_delay_ms" : 0.0
                                   }
     
        self.ResponseMatching = JuMEG_Epocher_ResponseMatching()       
    
#---    
    @property
    def event_data_stim_channel(self): return self.event_data_parameter["events"]["stim_channel"]
    @event_data_stim_channel.setter
    def event_data_stim_channel(self,v): self.event_data_parameter["events"]["stim_channel"]=v             

#---
    def channel_events_to_dataframe(self):
        """find events from stimulus [STI 014,ET_events] and response channels [STI 013]
        store as pandas dataframe and save in hdf5 obj key: /events
        """
       #--- stimulus channel group    
        for ch_idx in jumeg_base.picks.stim(self.raw):
            ch_label = jumeg_base.picks.picks2labels(self.raw,ch_idx)
            self.event_data_stim_channel = ch_label
            self._channel_events_dataframe_to_hdf(ch_label,"stim")
    
       #--- response channel group    
        for ch_idx in jumeg_base.picks.response(self.raw):
            ch_label = jumeg_base.picks.picks2labels(self.raw,ch_idx)
            self.event_data_stim_channel = ch_label
            self._channel_events_dataframe_to_hdf(ch_label,"resp")
          
#---      
    def _channel_events_dataframe_to_hdf(self,ch_label,prefix):
        """ save channel event dataframe to HDF obj
        Parameter
        ---------
        string      : channel label e.g.: 'STI 014'
        pd dataframe:
        dict        : info dict with parameter
        
        Results
        -------
        None
        """
        self.event_data_stim_channel = ch_label
        found = self.events_find_events(self.raw,prefix=prefix,**self.event_data_parameter)
        
        if found:
           df   = found[0]
           info = found[1] 
           #if type(df)  == "<class 'pandas.core.frame.DataFrame'>":
           key          = self.hdf_node_name_channel_events +"/"+ ch_label
           storer_attrs = {'info_parameter': info}
           self.hdf_obj_update_dataframe(df.astype(np.int64),key=key,**storer_attrs )       
        
#---
    def apply_iod_matching(self,raw=None):
        '''
        apply image-onset-detection (IOD),
        generate pandas dataframe with columns for iod    
        
        e.g. from template parameter for a condition
        "iod"  :{"marker"  :{"channel":"StimImageOnset","type_input":"img_onset","prefix":"img"},
                 "response":{"matching":true,"channel":"IOD","type_input":"iod_onset","prefix":"iod"}},
               
        Parameters
        ----------
        raw: obj [None]
             mne.raw obj
        
        Returns
        --------
        pandas dataframe columns with
        marker-prefix     => id,onset,offset
        response-prefix   => type,div,id,onset,offset,index,counts
        additionalcolumns => bads,selected,weighted_sel
        
        '''
        if not self.iod.iod_matching: return
        
      #--- marker events .e.g. STIMULUS
        mrk_df,mrk_info = self.events_find_events(raw,prefix=self.iod.marker.prefix,**self.iod.marker_channel_parameter)  
        
      #--- resonse eventse.g. IOD
        resp_df,resp_info = self.events_find_events(raw,prefix=self.iod.response.prefix,**self.iod.response_channel_parameter)
        if resp_info.get("system_delay_is_applied"):
           mrk_info["system_delay_is_applied"] = True
          
        #self.pp( mrk_df, head="  --> Response Matching --> IOD MRK/STIM IN" )
        #self.pp( resp_df,head="  --> Response Matching --> IOD RESP IN" )
        
        if self.verbose:
           self.pp( mrk_df,head=" --> Marker DF --> IOD out" )
           self.pp( resp_df,head=" --> Response DF --> IOD out" )
        
        df = self.ResponseMatching.apply(raw=raw,stim_df=mrk_df,resp_df=resp_df,
                                         stim_param      = self.iod.marker_channel_parameter.copy(),
                                         stim_type_input = self.iod.marker.type_input,
                                         stim_prefix     = self.iod.marker.prefix,
                                         resp_param      = self.iod.response_channel_parameter.copy(),
                                         resp_type_input = self.iod.response.type_input, 
                                         resp_prefix     = self.iod.response.prefix,
                                         verbose         = self.verbose
                                        )                              
         
        #sys.exit()
        return df,mrk_info  
    
#---    
    def update_parameter(self,param=None):
        '''update parameter
        -> init with default parameter
        -> merege and overwrite defaults with parameter defined for condition
        -> init special objs (marker,response,iod) if defined
                
        Parameter
        ---------
         param:  <None>
        
        '''
        self.marker    = None
        self.response  = None
        self.iod       = None
        self.parameter = None
        self.parameter = self.template_data['default'].copy()
        self.parameter = self.template_update_and_merge_dict(self.parameter,param)
  
        #if "marker" in self.parameter:  
        self.marker = JuMEG_Epocher_Events_Channel(label="marker",parameter=self.parameter)
        
        #if "response" in self.parameter:  
        self.response = JuMEG_Epocher_Events_Channel(label="response",parameter=self.parameter)
           
        #if "iod" in self.parameter:
        self.iod = JuMEG_Epocher_Events_Channel_IOD(label="iod",parameter=self.parameter)    
           
#---
    def events_store_to_hdf(self,fname=None,raw=None,condition_list=None,overwrite_hdf=False,
                            template_path=None,template_name=None,verbose=False):
        """find & store epocher data to hdf5:
        -> readding parameter from epocher template file
        -> find events from raw-obj using mne.find_events
        -> apply response matching if true
        -> save results in pandas dataframes & HDF fromat
        
        Parameter
        ---------
         fname         : string, fif file name <None>
         raw           : raw obj <None>
         condition_list: list of conditions to process
                         select special conditions from epocher template
                         default: <None> , will process all defined in template
         overwrite_hdf : flag for overwriting output HDF file <False>
         
         template_path : path to jumeg epocher templates
         template_name : name of template e.g: experimnet name 
         
         verbose       : flag, <False>

        Results
        -------
         raw obj 
         string: FIF file name 
        
        """
       
      #--- read template file  
        if template_name:
           self.template_name = template_name
        if template_path:
           self.template_path = template_path
        if verbose:
           self.verbose = verbose
         
        self.template_update_file()
  
        
        self.raw,fname = jumeg_base.get_raw_obj(fname,raw=raw)
       
       #---  init obj
        self.hdf_obj_init(raw=self.raw,overwrite=overwrite_hdf)
        
        self.channel_events_to_dataframe()
        
        if not condition_list :
           condition_list = self.template_data.keys()
       #--- condi loop
        # for condi, param, in self.template_data.iteritems():
        for condi in condition_list:
            param = self.template_data[condi]
          #--- check for real condition
            if condi == 'default': continue
          
          #--- check for condition in list
            if condi not in self.template_data.keys(): continue
          #--- update & merge condi self.parameter with defaults
            self.update_parameter(param=param)
            
            iod_data_frame = None
            
            self.line()
            print"===> Jumeg Epocher Events ====\n"
            print" --> Start Events Store into HDF"      
            print" --> condition: "+ condi
            self.line()
            
            if not self.marker.channel_parameter: continue
         
           #--- stimulus init dict's & dataframes
            marker_info         = dict()
            marker_data_frame   = pd.DataFrame()
            response_data_frame = pd.DataFrame()
            response_info       = dict()
                       
            if self.verbose:
               print' --> EPOCHER  Template: %s  Condition: %s' %(self.template_name,condi)
               print'  -> find events and epochs,  generate epocher output HDF5'
               #self.pp(self.parameter,head="  -> parameter")               
            
           #--- iod matching ckek if true and if channe == stimulus channel
            if self.iod.iod_matching:
               #self.pp(self.iod.parameter,"--->IOD Parameter:")
               iod_data_frame,iod_info = self.apply_iod_matching(raw=self.raw)
               if iod_data_frame is None: continue
               marker_data_frame = iod_data_frame
               marker_info       = iod_info
           
             #--- copy iod df to res or stim df 
               if self.response.matching:
                  if ( self.iod.marker.channel != self.marker.channel ):
                     response_data_frame = iod_data_frame
                     response_info       = iod_info
                    
           #--- ck if not stimulus_data_frame        
            if marker_data_frame.empty : 
               print"  -> MARKER CHANNEL -> find events => condition: "+ condi +" ---> marker channel: "+ self.marker.channel
               if self.verbose:
                  self.pp( self.marker.parameter,head="  -> Marker Channel parameter:")
               marker_data_frame,marker_info = self.events_find_events(self.raw,prefix=self.marker.prefix,**self.marker.channel_parameter)
           #---
            if marker_data_frame.empty: continue
            marker_data_frame['bads']             = 0
            marker_data_frame['selected']         = 0
            marker_data_frame['weighted_selected']= 0 
           #--- save stimulus event data to df to store in HDF
           # self.event_data_stim_channel = self.marker.stim_channel 
           # self.event_data_frames[self.marker.channel],self.event_data_info[self.marker.channel] = self.events_find_events(raw,prefix=self.marker.prefix,**self.event_data_parameter)
            
            if self.verbose:
               print"  -> Marker Epocher Events Data Frame [marker channel]: "+ condi
               print marker_data_frame
               print"\n"
            
           #--- Marker Matching task
           #--- match between stimulus and response or vice versa
           #--- get all response events for condtion e.g. button press 4
        
            if self.response.matching :
               print"  -> Marker Matching -> matching marker & response channel: " + condi
               print"  -> marker   channel : " + self.marker.channel
               print"  -> response channel : " + self.response.channel
             #--- look for all responses => 'event_id' = None
               if response_data_frame.empty:
                  res_channel_param = self.response.channel_parameter.copy()
                  res_channel_param['event_id']     = None
                  response_data_frame,response_info = self.events_find_events(self.raw,prefix=self.response.prefix,**res_channel_param)
                   
              # self.event_data_frames[self.response.channel] = response_data_frame
              # self.event_data_info[self.response.channel]   = response_info 
                
               if self.verbose:
                  print"---> Response Epocher Events Data Frame [response channel] : " + self.response.channel
                  print self.response.parameter
                     #print"---> Response Epocher Events Data Frame [respnse channel] : " + self.parameter['response_channel']
                  print response_data_frame
                  print"\n\n"

              #--- update stimulus epochs with response matching
               marker_data_frame = self.ResponseMatching.apply(raw=self.raw,verbose=self.verbose,
                                                               stim_df         = marker_data_frame,
                                                               stim_param      = self.marker.channel_parameter.copy(),
                                                               stim_type_input = self.marker.type_input,
                                                               stim_prefix     = self.marker.prefix,
                                                             #---  
                                                               resp_df         = response_data_frame,
                                                               resp_param      = self.response.channel_parameter.copy(),
                                                               resp_type_input = self.response.type_input, 
                                                               resp_type_offset= self.response.type_offset, 
                                                               resp_prefix     = self.response.prefix
                                                              )                       
           #---- not response matching should be all e.g. hits 
            else: 
               mrk_type = self.marker.prefix +'_type'  
               if mrk_type not in marker_data_frame :
                  marker_data_frame[ mrk_type ] = self.rt_type_as_index( self.marker.type_result ) 
                
                
                
            print "\n---> Marker DataFrame out:"
            print marker_data_frame
                
            key = self.hdf_node_name_epocher +'/'+condi
            storer_attrs = {'epocher_parameter': self.parameter,'info_parameter':marker_info}
            self.hdf_obj_update_dataframe(marker_data_frame.astype(np.int32),key=key,**storer_attrs )
         
        self.HDFobj.close()

        print" ---> DONE save epocher data into HDF5 :"
        print"  --> " + self.hdf_filename +"\n\n"
        return self.raw,fname

#---
    def events_find_events(self,raw,prefix=None,**param):
        """find events with <mne.find_events()>
        
        Parameters
        ---------
        raw   : raw obj
        prefix: prefix for columns <None> 
                
        param : parameter like <**kwargs>
               {'event_id': 40, 'and_mask': 255,
               'events': {'consecutive': True, 'output':'step','stim_channel': 'STI 014',
               'min_duration':0.002,'shortest_event': 2,'mask': 0}
                }

        Returns
        --------
        pandas data-frame with epoch event structure for e.g. stimulus, response channel
         id       : event id
         offset   : np array with TSL event code offset
         onset    : np array with TSL event code onset
         if <prefix>  columns are labeled with <prefix>
            e.g.: prefix=img => img_onset
        
         dict() with event structure for stimulus or response channel
          sfreq    : sampling frequency => raw.info['sfreq']
          duration : {mean,min,max}  in TSL
          system_delay_is_applied : True/False
          --> if true <system_delay_ms> converted to TSLs and added to the TSLs in onset,offset
                (TSL => timeslices,samples)
        """
        if raw is None:
           print "ERROR in  <get_event_structure: No raw obj \n"
           return 
        
       #---
        df = pd.DataFrame(columns = self.data_frame_stimulus_cols)

        ev_id_idx = np.array([])
        ev_onset  = np.array([])
        ev_offset = np.array([])
        
    #---add prefix to col name    
        if prefix:
           for k in self.data_frame_stimulus_cols:
               df.rename(columns={k: prefix+'_'+k},inplace=True )
           col_id    = prefix+"_id"
           col_onset = prefix+"_onset"
           col_offset= prefix+"_offset"
        else:
           col_id    = "id"
           col_onset = "onset"
           col_offset= "offset" 
       #---
        events           = param['events'].copy()
        events['output'] = 'step'
       # self.pp( events )
        ev = mne.find_events(raw, **events) #-- return int64

       #--- apply and mask e.g. 255 get the first 8 bits in Trigger channel
        if param['and_mask']:
           ev[:, 1:] = np.bitwise_and(ev[:, 1:], param['and_mask'])
           ev[:, 2:] = np.bitwise_and(ev[:, 2:], param['and_mask'])
    
        ev_onset  = np.squeeze( ev[np.where( ev[:,2] ),:])  # > 0
        ev_offset = np.squeeze( ev[np.where( ev[:,1] ),:])

        if param['event_id']:
           ev_id = jumeg_base.str_range_to_numpy(param['event_id'],exclude_zero=True)
           
           evt_ids=np.where(np.in1d(ev[:,2],ev_id))
           
          #--- check if code in events
           if len( np.squeeze(evt_ids) ):   
              ev_id_idx = np.squeeze( np.where( np.in1d( ev_onset[:,2],ev_id )))
              if ( ev_id_idx.size > 0 ):
                   ev_onset = ev_onset[ ev_id_idx,:]
                   ev_offset= ev_offset[ev_id_idx,:]
              else:
                  print'Warning => No such event code(s) found (ev_id_idx) -> event: ' + str( param['event_id'] )
                  return 
           else:
               print'Warning => No such event code(s) found (ev_id) -> event: ' + str(param['event_id'])
               return 

       #---- use all event ids
        if ( ev_onset.size == 0 ):
            print'Warning => No such event code(s) found -> event: ' + str(param['event_id'])
            return 
       #--- apply system delay if is defined e.g. auditory take`s 20ms to subjects ears
        if param['system_delay_ms']:
           system_delay_tsl = raw.time_as_index( param['system_delay_ms']/1000 ) # calc in sec
           ev_onset[:, 0] += system_delay_tsl
           ev_offset[:, 0]+= system_delay_tsl
           system_delay_is_applied = True
        else:
           system_delay_is_applied = False
       
        
       #-- avoid invalid index/dimension error if last offset is none
        df[col_id]     = ev_onset[:,2]
        df[col_onset]  = ev_onset[:,0]
        df[col_offset] = np.zeros( ev_onset[:,0].size,dtype=np.long )
        div = np.zeros( ev_offset[:,0].size )
        try:
            if ( ev_onset[:,0].size >= ev_offset[:,0].size ):
               div = ev_offset[:,0] - ev_onset[:ev_offset[:,0].size,0]
               df[col_offset][:ev_offset[:,0].size] = ev_offset[:,0]
        
            else:
               idx_max = ev_offset[:,0].size
               div = ev_offset[:,0] - ev_onset[:idx_max,0]    
               df[col_offset][:] = ev_offset[:idx_max,0]
        except:
            assert "ERROR dims onset offset will not fit\n"
        
        return df,dict( {
                         'sfreq'        : raw.info['sfreq'],
                         'duration'     :{'mean':np.rint(div.mean()),'min':div.min(),'max':div.max()},
                         'system_delay_is_applied' : system_delay_is_applied
                         } )
                                          

 
    
jumeg_epocher_events = JuMEG_Epocher_Events()

