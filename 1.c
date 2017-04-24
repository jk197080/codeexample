#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <malloc.h>
#include <windows.h>
#include <wingdi.h>
#include <math.h>

int main()
{
    //define variables
    BITMAPFILEHEADER bf;    //file head of .bmp files
    BITMAPINFOHEADER bi;    //info head of .bmp files
    FILE *fp;               //file pointer of the original file
    FILE *nfp;              //file pointer of the new magnitude file
    FILE *tfp;              //file pointer of histogram
    int i,j,k,flag,startOffset;
    char fileName[256];
    unsigned char oriImg[256][256]; //magnitude of pixels in original file
    unsigned char magImg[256][256]; //magnitude of pixels of new magnitude file
    unsigned char *buf; //a buffer to store temporary strings
    int theta[256][256];    //angle of every pixel
    int h[9]={0,0,0,0,0,0,0,0,0};   //9 items in histogram
    float c,r;  //r and c
    int the;    //angle
    int qa;
    int magnitude[256][256];    //magnitude of pixels

    
    //read original file
    printf("please enter filename:\n");
    scanf("%s",fileName);
    if(strstr(fileName,".bmp")) //if it is a bmp file then set flag to 1
    {
        flag=1;
    }else if(strstr(fileName,".raw"))   //if it is a raw file then set flag to 0
    {
        flag=0;
    }else
    {
        printf("wrong file\n");
        exit(0);
    }
    fp=fopen(fileName,"rb");
    if(fp == NULL)
    {
        printf("error!");
        exit(0);
    }

    //find the beginning of pixel data in .bmp files
    fread(&bf,sizeof(BITMAPFILEHEADER),1,fp);
    fread(&bi,sizeof(BITMAPINFOHEADER),1,fp);
    startOffset=(int)bf.bfOffBits;  //the start place of file in bmp files, here is 436h
    
    //store the header of bmp file in order to write into the new magnitude file
    buf=(unsigned char *)malloc(sizeof(unsigned char)*startOffset); //allocate a buffer
    fseek(fp,0,0);
    fread(buf,sizeof(unsigned char),startOffset,fp);

    //set the start
    if(flag==1) //if it is bmp, data shall start at the offset
    {
        fseek(fp,startOffset,0);
        for(i=255;i>=0;i--) //because it is a bmp file, the data start from the last line of the image to first line
        {
            for(j=0;j<256;j++)
            {
                fread(&oriImg[i][j],sizeof(unsigned char),1,fp);
            }
        }
    }
    else    //if it is raw, data shall start at the beginning
    {
    	fseek(fp,0,0);
        for(i=0;i<256;i++)
        {
            for(j=0;j<256;j++)
            {
                fread(&oriImg[i][j],sizeof(unsigned char),1,fp);
            }
        }
    }
    
    //calculate the original magnitude angle and quantized angle for every pixel in the whole image
    for(i=0;i<256;i++)
    {
        for(j=0;j<256;j++)
        {
        	if(i!=0&&i!=255&&j!=0&&j!=255)  //border should be different
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
        		    the=(int)(180-atan2(r,c)*180/3.14159)%180;  //negated angle
        		    theta[i][j]=the/20+1;   //quantize the angle
                }

        	}
        	else    
        	{
        		magImg[i][j]=0;
                magnitude[i][j]=0;
        		theta[i][j]=-1;
        	}
        }
    }
    
    //store the file, for bmp and raw respectively
    
    if(flag==1) //bmp
    {
    	nfp=fopen("mag.bmp","wb+");
    	if(nfp == NULL)
    	{
    	    printf("error!");
    	    exit(0);
    	}
    	fwrite(buf,sizeof(unsigned char),startOffset,nfp);  //write the header of bmp file

    	for(i=255;i>=0;i--) //from the last line to first line
    	{
    	    for(j=0;j<256;j++)
    	    {
    	        fwrite(&magImg[i][j],sizeof(unsigned char),1,nfp);
    	    }
    	}
    	fseek(fp,-2,2); //fill the file
    	fread(buf,sizeof(unsigned char),2,fp);
    	fwrite(buf,sizeof(unsigned char),2,nfp);
    	free(buf);
    }
    else    //raw
    {
    	nfp=fopen("mag.raw","wb+");
    	if(nfp == NULL)
    	{
    	    printf("error!");
    	    exit(0);
    	}
    	for(i=0;i<256;i++)
    	{
    	    for(j=0;j<256;j++)
    	    {
    	    	 fwrite(&magImg[i][j],sizeof(unsigned char),1,nfp); //write from the beginning of the file
    	    }
    	}
    }

    //open histogram file
    tfp=fopen("histograms.txt","w+");
    if(tfp==NULL)
    {
    	printf("error!");
    	exit(0);
    }

    

        float t;
        float ave;
        for(k=0;k<256;k++)  //256 cells in total
        {
            //add up all magnitude for the cell then calculate the average
            t=0.0;
            ave=0.0;
            for(i=k-k%16;i<k-k%16+16;i++)
            {
        	    for(j=k%16*16;j<k%16*16+16;j++)
    	        {
                    if(theta[i][j]!=-1)
                    {
                        t++;    //all valid pixels
                        ave+=(float)magnitude[i][j];    //all magnitude
                    }
                }
            }

            ave=ave/t;  //get the average magnitude


            //add vote
            for(i=0;i<9;i++)
            {
    	        h[i]=0;
            }
    	    for(i=k-k%16;i<k-k%16+16;i++)
            {
        	    for(j=k%16*16;j<k%16*16+16;j++)
    	        {   
                    if(theta[i][j]!=-1)
    			    {
                        theta[i][j]=(int)(theta[i][j]+round((float)magnitude[i][j]/ave)-1)%9+1; //calculate the vote and add into the original quantized angle
    			    	h[theta[i][j]-1]++; //add one into histogram
        	    	}
            	}
    	    }

            //print the histogram
        	for(i=0;i<9;i++)
            {
    	        fprintf(tfp,"%d ",h[i]);
            }
            fprintf(tfp,"\n");
        }
        
    fclose(fp);
    fclose(nfp);
    fclose(tfp);
    return 0;
}
