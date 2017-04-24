#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <malloc.h>
#include <windows.h>
#include <wingdi.h>
#include <math.h>
#define DD 3780

float positive[10][DD];		//to store the descriptor of 10 positive training images
float negative[10][DD];		//to store the descriptor of 10 negative training images
float test[DD];				//to store the descriptor of every testing file
float posmean[DD];			//to store the mean descriptor of positive training images
float negmean[DD];			//to store the mean descriptor of negative training images
float w[DD];				//to store and calculate the value of W
char testfileName[256];		//to pass the test file names
char bmp[5]=".bmp";			//bmp

//module to calculate the descriptor
int calcdes(int x,int type)
{
    //define variables
    BITMAPFILEHEADER bf;    //file head of .bmp files
    BITMAPINFOHEADER bi;    //info head of .bmp files
    FILE *fp;               //file pointer of the original file
    int i,j,k,flag,startOffset;
	unsigned char color[3];	//every pixel has 3 color, to save the colors
    char fileName[256];		//pass the filename
	char pathName[256];		//pass the pathname
	char testpathName[256];	//pass the testpathname
	int grayscale;			//to store the grayscale of every pixel
	float blue,green,red;	//3 colors
    unsigned char oriImg[160][96]; //magnitude of pixels in original file
    unsigned char magImg[160][96]; //magnitude of pixels of new magnitude file
    unsigned char *buf; //a buffer to store temporary strings
    float theta[160][96];    //angle of every pixel 
    float h[9];   //9 items in histogram
	float histogram[240][9];
	float block[105][36];
    float c,r;  //r and c
    float the;    //angle
    int qa;
    int magnitude[160][96];    //magnitude of pixels
    float ave;			//average
	//FILE *mfp;
	//char magfileName[256];
	
	itoa(x,fileName,10);	//to pass the filename
	strcat(fileName,bmp);	//to pass the filename
    
	//itoa(x,magfileName,10);
	//strcat(magfileName,"mag.raw");
	
	if(type==0)		//for training positive set
	{
		strcpy(pathName,".\\training set\\positive samples\\");
		strcat(pathName,fileName);
		//printf("%s\n",pathName);
		fp=fopen(pathName,"rb");		//open file
		//strcpy(pathName,".\\training set\\positive samples\\");
		//strcat(pathName,magfileName);
		//mfp=fopen(pathName,"wb+");
	}
	else if(type==1)		//for training negative set
	{
		strcpy(pathName,".\\training set\\negative samples\\");
		strcat(pathName,fileName);
		fp=fopen(pathName,"rb");
		//strcpy(pathName,".\\training set\\negative samples\\");
		//strcat(pathName,magfileName);
		//mfp=fopen(pathName,"wb+");
	}
	else		//for testing set
	{
		strcpy(testpathName,".\\testing set\\");
		strcat(testpathName,testfileName);
		fp=fopen(testpathName,"rb");
		//strcpy(testpathName,".\\testing set\\");
		//strcat(testpathName,magfileName);
		//mfp=fopen(testpathName,"wb+");
	}

    if(fp == NULL)
    {
        printf("error!");
        exit(0);
    }

    //find the beginning of pixel data in .bmp files
    fread(&bf,sizeof(BITMAPFILEHEADER),1,fp);
    fread(&bi,sizeof(BITMAPINFOHEADER),1,fp);
    startOffset=(int)bf.bfOffBits; 
    
    //store the header of bmp file in order to write into the new magnitude file
    buf=(unsigned char *)malloc(sizeof(unsigned char)*startOffset); //allocate a buffer
    fseek(fp,0,0);
    fread(buf,sizeof(unsigned char),startOffset,fp);
	//printf("%d\n",startOffset);
    //set the start
    fseek(fp,startOffset,0);
    for(i=159;i>=0;i--) //because it is a bmp file, the data start from the last line of the image to first line
    {
        //to calculate the grayscale of every pixel
		for(j=0;j<96;j++)
        {
			fread(&color[0],sizeof(unsigned char),1,fp);
			fread(&color[1],sizeof(unsigned char),1,fp);
			fread(&color[2],sizeof(unsigned char),1,fp);
			blue=(float)color[0];
			green=(float)color[1];
			red=(float)color[2];
			grayscale=(int)(red*0.299+green*0.587+blue*0.114);
			oriImg[i][j]=(unsigned char)grayscale;
        }
    }

   
    //calculate the original magnitude angle and quantized angle for every pixel in the whole image
    for(i=0;i<160;i++)
    {
        for(j=0;j<96;j++)
        {
        	if(i!=0&&i!=159&&j!=0&&j!=95)  //border should be different
        	{
        		r=(float)(oriImg[i][j+1]-oriImg[i][j-1]);   //apply two matrix
        		c=(float)(oriImg[i+1][j]-oriImg[i-1][j]);
        		magnitude[i][j] = round(sqrt(r*r*0.5+c*c*0.5));
        		magImg[i][j]=(unsigned char)magnitude[i][j];    //prepare the data for storing
                if(r==0.0&&c==0.0)  //if r=c=0, then the angle of this pixel should be undefined
                {
                    theta[i][j]=-1;
                }
                else
                {
        		    the=fmod((180.0-atan2(r,c)*180.0/3.14159),180.0);  //negated angle
        		    theta[i][j]=the;
                }
        	}
        	else    
        	{
        		magImg[i][j]=0;
                magnitude[i][j]=0;
        		theta[i][j]=-1.0;
        	}
        }
    }

    float vj;
	int cj;
	int jj;
    //for every pixel, compute the histogram
	for(k=0;k<240;k++)  //240 cells in total
    {
        for(i=0;i<9;i++)
        {
 	        h[i]=0.0;
        }
  	    for(i=8*(k/12);i<8*(k/12)+8;i++)
        {
     	    for(j=k%12*8;j<k%12*8+8;j++)
   	        {   
                if(theta[i][j]!=-1.0)
   			    {
                    jj=(int)(floor(theta[i][j]/20.0+8.5))%9;
					vj=(float)magnitude[i][j]*(fmod((((float)jj+1.5)*20.0-theta[i][j]+180.0),180.0))/20.0;	//vote of magnitude for every pixel
					h[jj]+=vj;
					vj=(float)magnitude[i][j]*fmod((theta[i][j]-((float)jj+0.5)*20.0+180.0),180.0)/20.0;
					h[(jj+1)%9]+=vj;	//vote of magnitude for every pixel
       	    	}
           	}
   	    }

		for(i=0;i<9;i++)
        {
 	        histogram[k][i]=h[i];
			//printf("%d\n",h[i]);
        }
    }
	//catenate the histogram of 4 cells into 1 block
	for(i=0;i<15;i++)
	{
		for(j=0;j<7;j++)
		{
			ave=0.0;
			//first cell
			for(k=0;k<9;k++)
			{
				block[7*i+j][k]=(float)histogram[26+12*i+j][k%9];
			}
			//second cell
			for(k=9;k<18;k++)
			{
				block[7*i+j][k]=(float)histogram[26+12*i+1+j][k%9];
			}
			//third cell
			for(k=18;k<27;k++)
			{
				block[7*i+j][k]=(float)histogram[26+12*i+12+j][k%9];
			}
			//fourth cell
			for(k=27;k<36;k++)
			{
				block[7*i+j][k]=(float)histogram[26+12*i+12+1+j][k%9];
			}
			//calculate the average magnitude of every block
			for(k=0;k<36;k++)
			{
				ave+=(block[7*i+j][k])*(block[7*i+j][k]);
			}
			//some histogram value can be 0, which cannot be devided
			if(ave<0.00000000000000001)
			{
				ave=0.00000000000000001;
			}
			ave=sqrt(ave);
			//get the final histogram
			for(k=0;k<36;k++)
			{
				block[7*i+j][k]=block[7*i+j][k]/ave;
			}
		}
	}
	//store the descriptor to every array of the different kind of images
	if(type==0)
	{
		for(i=0;i<DD;i++)
		{
			positive[x][i]=block[i/36][i%36];
		}
    }
	else if(type==1)
	{
		for(i=0;i<DD;i++)
		{
			negative[x][i]=block[i/36][i%36];
		}
	}
	else
	{
		for(i=0;i<DD;i++)
		{
			test[i]=block[i/36][i%36];
		}
	}
	//store the magnitude file
	//for(i=0;i<160;i++)
    //	{
    //	    for(j=0;j<96;j++)
    //	    {	
	//   	    	fwrite(&magImg[i][j],sizeof(unsigned char),1,mfp); //write from the beginning of the file
    //	    }
    //	}
	//fclose(mfp);
	
	fclose(fp);
	
	//reset all the arrays
	memset(color,0,3);
	memset(fileName,0,256);
	memset(pathName,0,256);
	memset(testpathName,0,256);	
	memset(oriImg,0,15360);
	memset(magImg,0,15360);
	memset(buf,0,4);
	memset(theta,0,15360);
	memset(h,0,9);
	memset(histogram,0,2160);
	memset(block,0,3780);
	memset(magnitude,0,15360);
	return 0;
}



//calculate the w using all the training set
void calcw()
{
	float alpha=0.1;		//alpha
	int i,j,k;
	int flag=1;			//to determine if the iteration need to be stopped
	int iteration=0;		//to calculate the iteration number
	float sum;
	//initial w
	for(i=0;i<DD;i++)
	{
		w[i]=(float)((-1)^(i%2));
	}

	//iteration
	while(flag!=0)
	{
		flag=0;
		for(j=0;j<10;j++)
		{
			//first to use positive image
			sum=0.0;
			for(i=0;i<DD;i++)
			{
				sum+=positive[j][i]*w[i];
			}

			if(sum<=0.0)
			{
				flag++;
				for(i=0;i<DD;i++)
				{
					w[i]+=alpha*positive[j][i];
				}
			}
			//then negative image
			sum=0.0;
			for(i=0;i<DD;i++)
			{
				sum+=negative[j][i]*w[i];
			}
			if(sum>=0.0)
			{
				flag++;
				for(i=0;i<DD;i++)
				{
					w[i]-=alpha*negative[j][i];
				}
			}
			
		}
		//printf("%d\n",flag);
		iteration++;
	}
	printf("the iteration time is %d\n",iteration);
}


//calculate the euclidean distance for every training image
void eucdis()
{
	int i,j;
	float sum;
	//positive mean descriptor
	for(i=0;i<DD;i++)
	{
		sum=0.0;
		for(j=0;j<10;j++)
		{
			sum+=positive[j][i];
		}
		posmean[i]=sum/10;
	}
	//distance of every positive image
	for(i=0;i<10;i++)
	{
		sum=0.0;
		for(j=0;j<DD;j++)
		{
			sum +=(posmean[j]-positive[i][j])*(posmean[j]-positive[i][j]);
		}
		sum = sqrt(sum);
		printf("the Euclidean distance from positive sample %d to mean descriptor is %.2f\n",i,sum);
	}
	
	//negative mean descriptor	
	for(i=0;i<DD;i++)
	{
		sum=0.0;
		for(j=0;j<10;j++)
		{
			sum+=negative[j][i];
		}
		negmean[i]=sum/10.0;
	}
	//distance of every negative image
	for(i=0;i<10;i++)
	{
		sum=0.0;
		for(j=0;j<DD;j++)
		{
			sum +=(negmean[j]-negative[i][j])*(negmean[j]-negative[i][j]);
		}
		sum = sqrt(sum);
		printf("the Euclidean distance from negative sample %d to mean descriptor is %.2f\n",i,sum);
	}
}


//determine every testing set contains a person
int testsamples()
{
	int i;
	float sum=0.0;
	calcdes(0,2);
	//calculate the sum
	for(i=0;i<DD;i++)
	{
		sum+=test[i]*w[i];
	}
	//determine
	if(sum>0)
	{
		printf("contains a people\n");
	}
	else if(sum<0)
	{
		printf("does not contain a people\n");
	}
	else
	{
		printf("not decided");
	}
	printf("%.2f\n",sum);
	return 1;
}


int main()
{
	int i,j,k,ii;
	FILE *pfp;
	FILE *nfp;
	char fileName[256];
	//first to calculate the descriptors of every training image
	for(i=0;i<10;i++)
	{
		calcdes(i,0);
	}
	for(i=0;i<10;i++)
	{
		calcdes(i,1);
	}
	//for(i=0;i<10;i++)
	//{
	//	printf("%.2f\n",positive[i][0]);
	//}
	//for(i=0;i<10;i++)
	//{
	//	printf("%.2f\n",negative[i][0]);
	//}
	//outputs
	pfp=fopen("crop001030c.txt","w+");
	k=0;
	for(i=0;i<105;i++)
	{
		for(j=0;j<36;j++)
		{
			fprintf(pfp,"%.2f ",positive[0][k]);
			k++;
		}
		fprintf(pfp,"\n");
	}
	fclose(pfp);
	//outputs
	pfp=fopen("crop001034b.txt","w+");
	k=0;
	for(i=0;i<105;i++)
	{
		for(j=0;j<36;j++)
		{
			fprintf(pfp,"%.2f ",positive[1][k]);
			k++;
		}
		fprintf(pfp,"\n");
	}
	fclose(pfp);
	//outputs
	nfp=fopen("00000003a_cut.txt","w+");
	k=0;
	for(i=0;i<105;i++)
	{
		for(j=0;j<36;j++)
		{
			fprintf(nfp,"%.2f ",negative[0][k]);
			k++;
		}
		fprintf(nfp,"\n");
	}
	fclose(nfp);
	//outputs
	nfp=fopen("00000057a_cut.txt","w+");
	k=0;
	for(i=0;i<105;i++)
	{
		for(j=0;j<36;j++)
		{
			fprintf(nfp,"%.2f ",negative[1][k]);
			k++;
		}
		fprintf(nfp,"\n");
	}
	fclose(nfp);
	//calculate the final W
	calcw();
	//calculate the euclidean distance
	eucdis();
	
	FILE *tfp;
	//outputs
	for(i=0;i<5;i++)
	{
		printf("testing set positive image number: %d ",i);
		itoa(i,fileName,10);
		strcat(fileName,bmp);
		strcpy(testfileName,"positive\\");
		strcat(testfileName,fileName);
		testsamples();
		if(i==0)
		{
			tfp=fopen("crop001008b.txt","w+");
			k=0;
			for(ii=0;ii<105;ii++)
			{
				for(j=0;j<36;j++)
				{
					fprintf(tfp,"%.2f ",test[k]);
					k++;
				}
				fprintf(tfp,"\n");
			}
			fclose(tfp);
		}
	}
	//outputs
	for(i=0;i<5;i++)
	{
		printf("testing set negative image number: %d ",i);
		itoa(i,fileName,10);
		strcat(fileName,bmp);
		strcpy(testfileName,"negative\\");
		strcat(testfileName,fileName);
		testsamples();
		if(i==0)
		{
			tfp=fopen("00000053a_cut.txt","w+");
			k=0;
			for(ii=0;ii<105;ii++)
			{
				for(j=0;j<36;j++)
				{
					fprintf(tfp,"%.2f ",test[k]);
					k++;
				}
				fprintf(tfp,"\n");
			}
			fclose(tfp);
		}
	}
	//outputs
	tfp=fopen("positive mean descriptor.txt","w+");
	k=0;
	for(ii=0;ii<105;ii++)
	{
		for(j=0;j<36;j++)
		{
			fprintf(tfp,"%.2f ",posmean[k]);
			k++;
		}
		fprintf(tfp,"\n");
	}
	fclose(tfp);
	//outputs
	tfp=fopen("negative mean descriptor.txt","w+");
	k=0;
	for(ii=0;ii<105;ii++)
	{
		for(j=0;j<36;j++)
		{
			fprintf(tfp,"%.2f ",negmean[k]);
			k++;
		}
		fprintf(tfp,"\n");
	}
	fclose(tfp);
	//while(1)
	//{
		//printf("please enter testfilename:\n");
		//scanf("%s",testfileName);
		//printf("%s\n",testfileName);
		//testsamples();
	//}
	//for(i=0;i<100;i++)
	//{
		//printf("%.3f ",negmean[i]);
	//}
	return 0;
}
