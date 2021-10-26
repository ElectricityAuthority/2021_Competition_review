#======================================
#Update 30 June 2021
#This code is for Github 
#======================================
#Dynamic regression 
#======================================
#load packages
library(zoo)
library(lmtest)
library(forecast)
library(urca)
#======================================
#PPI and trend adjustments
elppiq <- read.csv("PPIQelectricity2017_2.csv")
elppiq <- ts(elppiq[,2],start=c(1994,2),end=c(2021,2),freq=4)

usedays=31+28+31+30+31+30 #from 1 Jan to 30 June (assume 365 days, note data is shaped to 365 days a year)
tmp <- approx(time(lag(elppiq,-1)),log(elppiq),xout=seq(2014,2021,usedays/365)) 
elppi <- exp(ts(tmp$y[-1],start=c(2014,1),end=c(2021,usedays),freq=365)) 

p2=read.csv("alldata_daily_June2021_v2a_1.csv") #note: price is PPI and trend adjusted
p2<-p2[,-c(1)]
ynom<-p2$price
length(ynom);length(elppi)
#Check if the data has NaN
isTRUE(all.equal(length(ynom), length(elppi))) #if TRUE, check
#Adjust price by PPI and trend
yreal<-ynom*elppi[length(elppi)]/elppi
p2$yreal<-yreal

timey<-time(elppi)
par(mfrow=c(1,1))
plot(timey,ynom, type='l',ylim=c(0,600),ylab='Spot price ($/MWh)',xlab='',xaxt='n')
axis(1,seq(2014,2021,1),cex.axis=1)
lines(yreal, col=2)
write.csv(p2,"alldata_daily_forDRM_2.csv")
#=======================================================================================================
#Dynamic Regression
dd <- read.csv("alldata_daily_forDRM_2.csv")
dd<-dd[,-c(1)]
dd$Date = as.Date(dd$Date, format = "%Y-%m-%d")

par(mfrow=c(1,2))
acf(dd$price)
pacf(dd$price)

acf(dd$yreal, main="ACF", xlab='')
pacf(dd$yreal, main="PACF",xlab='')

#add dummy
date1 <- as.Date("2018-09-28")
#dummy 1: UTS1 time is from 28 September 2018 onwards
dd$dummy <- ifelse(dd$Date >= date1,1,0)

dayOfYear = as.numeric(format(dd[1,1], "%j"))
dayOfYear2 = as.numeric(format(max(dd$Date), "%j"))

#Make variables in time series
dummy<-ts(dd$dummy, start = c(2014, dayOfYear), end=c(2021,dayOfYear2),frequency = 365)
ynom = ts(dd$price, start = c(2014, dayOfYear), end=c(2021,dayOfYear2),frequency = 365)
yreal<-ts(dd$yreal, start = c(2014, dayOfYear), end=c(2021,dayOfYear2),frequency = 365)
dd$Storage1<-dd$Storage-dd$mean_storage #adjust storage 
stor<-ts(dd$Storage1, start = c(2014, dayOfYear), end=c(2021,dayOfYear2),frequency = 365)
demand<-ts(dd$Demand_GWh, start = c(2014, dayOfYear), end=c(2021,dayOfYear2),frequency = 365)
windgen<-ts(dd$Wind_gen_GW,start = c(2014, dayOfYear), end=c(2021,dayOfYear2), frequency = 365)
rollinggasp<-ts(dd$weekly_rolling_average, start = c(2014, dayOfYear), end=c(2021,dayOfYear2), frequency = 365)
genhhi<-ts(dd$HHI,start = c(2014, dayOfYear), end=c(2021,dayOfYear2), frequency = 365)
offers<-ts(dd$All_Offered,start = c(2014, dayOfYear), end=c(2021,dayOfYear2), frequency = 365)
generation<-ts(dd$All_Generation,start = c(2014, dayOfYear), end=c(2021,dayOfYear2), frequency = 365)
Ahuroa_gas<-ts(dd$Ahuroa_gas,start = c(2014, dayOfYear), end=c(2021,dayOfYear2), frequency = 365)
carbonprice<-ts(dd$carbon,start = c(2014, dayOfYear), end=c(2021,dayOfYear2), frequency = 365)
coalprice<-ts(dd$coal,start = c(2014, dayOfYear), end=c(2021,dayOfYear2), frequency = 365)

#Test for stationary
df.yreal=ur.df(yreal)
summary(df.yreal)#stationary 

#storage
df.stor=ur.df(stor)
summary(df.stor)#stationary

#demand
df.demand=ur.df(demand)
summary(df.demand)
ddema<-diff(demand)
df.ddema=ur.df(ddema)
summary(df.ddema) #stationary

#wind
df.windgen=ur.df(windgen)
summary(df.windgen) #stationary 

#gas price
rollinggasp[is.na(rollinggasp)] <- 5.789915
df.rolgasp=ur.df(rollinggasp)
summary(df.rolgasp) #nonstationary 
drollinggasp<-diff(rollinggasp)
df.drollinggasp=ur.df(drollinggasp)
summary(df.drollinggasp)#stationary 

#generation HHI
df.genhhi<-ur.df(genhhi)
summary(df.genhhi) #non-stationary 
dgenhhi<-diff(genhhi)
df.dgenhhi<-ur.df(dgenhhi)
summary(df.dgenhhi)#stationary 

#offers
df.offers=ur.df(offers)
summary(df.offers) #non-stationary 
doffers<-diff(offers)
df.doffers=ur.df(doffers)
summary(df.doffers) #stationary 

#generation
df.generation<-ur.df(dd$All_Generation)
summary(df.generation) #non-stationary
dgen<-diff(generation)
df.dgen<-ur.df(dgen)
summary(df.dgen)#stationary

ratio_raw<-offers/generation
df.ratio_raw<-ur.df(ratio_raw)
summary(df.ratio_raw)#non-stationary

#ratio of adjusted offer to adjusted generation
ratio<-doffers/dgen
df.ratio<- ur.df(ratio) 
summary(df.ratio)#stationary

#Ahuroa_gas
which(is.na(Ahuroa_gas))
df.Ahuroa_gas<- ur.df(Ahuroa_gas)
summary(df.Ahuroa_gas)#non-stationary
dahuroa<-diff(Ahuroa_gas)
df.dahuroa<-ur.df(dahuroa)
summary(df.dahuroa)#stationary
par(mfrow=c(1,1))
plot(Ahuroa_gas, ylab='Ahuroa gas storage PJ', xlab='')

#carbon price
which(is.na(carbonprice))
df.carbonprice<- ur.df(carbonprice)
summary(df.carbonprice)#non-stationary
dcarbonp<-diff(carbonprice)
df.dcarbonp<-ur.df(dcarbonp)
summary(df.dcarbonp)#stationary

#Coal
which(is.na(coalprice))
df.coalprice<- ur.df(coalprice)
summary(df.coalprice)#non-stationary
dcoalp<-diff(coalprice)
df.dcoalp<-ur.df(dcoalp)
summary(df.dcoalp)#stationary

#Modeling 
#x1<-cbind(stor,ddema,windgen,drollinggasp,dgenhhi,dahuroa,dcarbonp,dcoalp,ratio,dd$dummy) #full model
#drop dcoalp, dcarbonp, ratio one by one based on the p-values
#x1<-cbind(stor,ddema,windgen,drollinggasp,dgenhhi,dahuroa,dd$dummy) 
#drop dgenhhi
#x1<-cbind(stor,ddema,windgen,drollinggasp,dahuroa,dd$dummy)
#drop dahuroa due to non-significant
x1<-cbind(stor,ddema,windgen,drollinggasp,dd$dummy) #model in the report

ts.fit.s<-auto.arima(yreal,xreg=x1,d=0,trace=T) #yreal is stationary, so set d=0
summary(ts.fit.s)
coeftest(ts.fit.s)

#Check residuals
cbind("Regression Errors" = residuals(ts.fit.s, type="regression"),
      "ARIMA errors" = residuals(ts.fit.s, type="innovation")) %>%
  autoplot(facets=TRUE)
Box.test(residuals(ts.fit.s))
#===============================================================================
