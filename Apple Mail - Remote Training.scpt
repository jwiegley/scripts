FasdUAS 1.101.10   ��   ��    k             l     ��  ��    #  Apple Mail - Remote Training     � 	 	 :   A p p l e   M a i l   -   R e m o t e   T r a i n i n g   
  
 l     ��  ��    I C https://c-command.com/scripts/spamsieve/apple-mail-remote-training     �   �   h t t p s : / / c - c o m m a n d . c o m / s c r i p t s / s p a m s i e v e / a p p l e - m a i l - r e m o t e - t r a i n i n g      l     ��  ��    V P Summary: Training script for setting up a spam filtering drone with Apple Mail.     �   �   S u m m a r y :   T r a i n i n g   s c r i p t   f o r   s e t t i n g   u p   a   s p a m   f i l t e r i n g   d r o n e   w i t h   A p p l e   M a i l .      l     ��  ��    &   Requires: SpamSieve, Apple Mail     �   @   R e q u i r e s :   S p a m S i e v e ,   A p p l e   M a i l      l     ��  ��    m g Install Location: ~/Library/Application Scripts/com.apple.mail or ~/Library/Scripts/Applications/Mail/     �   �   I n s t a l l   L o c a t i o n :   ~ / L i b r a r y / A p p l i c a t i o n   S c r i p t s / c o m . a p p l e . m a i l   o r   ~ / L i b r a r y / S c r i p t s / A p p l i c a t i o n s / M a i l /      l     ��   !��        Last Modified: 2022-12-27    ! � " " 4   L a s t   M o d i f i e d :   2 0 2 2 - 1 2 - 2 7   # $ # l     ��������  ��  ��   $  % & % l     ��������  ��  ��   &  ' ( ' l     ��������  ��  ��   (  ) * ) j     �� +�� .0 pmarkspammessagesread pMarkSpamMessagesRead + m     ��
�� boovfals *  , - , j    �� .�� (0 pcolorspammessages pColorSpamMessages . m    ��
�� boovtrue -  / 0 / j    �� 1�� &0 pflagspammessages pFlagSpamMessages 1 m    ��
�� boovfals 0  2 3 2 j   	 �� 4�� 20 pmarkgoodmessagesunread pMarkGoodMessagesUnread 4 m   	 
��
�� boovfals 3  5 6 5 j    �� 7�� .0 pmovebysettingmailbox pMoveBySettingMailbox 7 m    ��
�� boovtrue 6  8 9 8 j    �� :�� $0 pspammailboxname pSpamMailboxName : m     ; ; � < <  S p a m 9  = > = j    �� ?�� *0 penabledebuglogging pEnableDebugLogging ? m    ��
�� boovfals >  @ A @ p     B B ������  0 usejunkmailbox useJunkMailbox��   A  C D C l     ��������  ��  ��   D  E F E i     G H G I      �������� ,0 accountnamesfordrone accountNamesForDrone��  ��   H k      I I  J K J l     �� L M��   L q k Enter your account names here. If you have more than one, separate with commas: {"Account 1", "Account 2"}    M � N N �   E n t e r   y o u r   a c c o u n t   n a m e s   h e r e .   I f   y o u   h a v e   m o r e   t h a n   o n e ,   s e p a r a t e   w i t h   c o m m a s :   { " A c c o u n t   1 " ,   " A c c o u n t   2 " } K  O P O l     �� Q R��   Q e _ The account name comes from the "Description" field in the Accounts tab of Mail's preferences.    R � S S �   T h e   a c c o u n t   n a m e   c o m e s   f r o m   t h e   " D e s c r i p t i o n "   f i e l d   i n   t h e   A c c o u n t s   t a b   o f   M a i l ' s   p r e f e r e n c e s . P  T�� T L      U U J      V V  W�� W m      X X � Y Y  A c c o u n t   1��  ��   F  Z [ Z l     ��������  ��  ��   [  \ ] \ i     ^ _ ^ I      �������� 60 spammailboxnamesbyaccount spamMailboxNamesByAccount��  ��   _ k      ` `  a b a l     �� c d��   c ` Z You can specify pairs here, e.g. {{"Work Account", "Junk"}, {"Personal Account", "Spam"}}    d � e e �   Y o u   c a n   s p e c i f y   p a i r s   h e r e ,   e . g .   { { " W o r k   A c c o u n t " ,   " J u n k " } ,   { " P e r s o n a l   A c c o u n t " ,   " S p a m " } } b  f g f l     �� h i��   h ] W to have different spam mailbox names for each account. If an account is not specified,    i � j j �   t o   h a v e   d i f f e r e n t   s p a m   m a i l b o x   n a m e s   f o r   e a c h   a c c o u n t .   I f   a n   a c c o u n t   i s   n o t   s p e c i f i e d , g  k l k l     �� m n��   m ' ! it defaults to pSpamMailboxName.    n � o o B   i t   d e f a u l t s   t o   p S p a m M a i l b o x N a m e . l  p�� p L      q q J     ����  ��   ]  r s r l     ��������  ��  ��   s  t u t i      v w v I      �������� $0 hostnamefordrone hostNameForDrone��  ��   w k      x x  y z y L      { { m      | | � } }   z  ~  ~ l   �� � ���   � K E Remove the above line if iCloud rule syncing is working incorrectly,    � � � � �   R e m o v e   t h e   a b o v e   l i n e   i f   i C l o u d   r u l e   s y n c i n g   i s   w o r k i n g   i n c o r r e c t l y ,   � � � l   �� � ���   � G A so that your remote training rule cannot be made inactive on the    � � � � �   s o   t h a t   y o u r   r e m o t e   t r a i n i n g   r u l e   c a n n o t   b e   m a d e   i n a c t i v e   o n   t h e �  � � � l   �� � ���   �   non-drone Macs.    � � � �     n o n - d r o n e   M a c s . �  � � � r     � � � n    � � � I    �� �����  0 lookupdefaults lookupDefaults �  � � � J     � �  ��� � m     � � � � � 0 A p p l e M a i l E n a b l e d H o s t N a m e��   �  ��� � J    
 � �  ��� � m     � � � � �  ��  ��  ��   �  f     � J       � �  ��� � o      ���� 	0 _host  ��   �  ��� � L     � � o    ���� 	0 _host  ��   u  � � � l     ��������  ��  ��   �  � � � i   ! $ � � � I      �� ����� 0 debuglog debugLog �  ��� � o      ���� 0 _message  ��  ��   � Z     � ����� � o     ���� *0 penabledebuglogging pEnableDebugLogging � n    � � � I   	 �� ����� 0 logtoconsole logToConsole �  ��� � o   	 
���� 0 _message  ��  ��   �  f    	��  ��   �  � � � l     ��������  ��  ��   �  � � � i   % ( � � � I      �� ����� 0 logtoconsole logToConsole �  ��� � o      ���� 0 _message  ��  ��   � k      � �  � � � r      � � � b      � � � m      � � � � � \ S p a m S i e v e   [ A p p l e   M a i l   R e m o t e   T r a i n i n g   M J T L o g ]   � o    ���� 0 _message   � o      ���� 0 _logmessage _logMessage �  ��� � I   �� ���
�� .sysoexecTEXT���     TEXT � b     � � � m     � � � � � & / u s r / b i n / l o g g e r   - s   � n   
 � � � 1    
��
�� 
strq � o    ���� 0 _logmessage _logMessage��  ��   �  � � � l     ��������  ��  ��   �  � � � i   ) , � � � I     ������
�� .aevtoappnull  �   � ****��  ��   � k      � �  � � � l     �� � ���   � 9 3 This is executed when you run the script directly.    � � � � f   T h i s   i s   e x e c u t e d   w h e n   y o u   r u n   t h e   s c r i p t   d i r e c t l y . �  ��� � n     � � � I    �������� $0 doremotetraining doRemoteTraining��  ��   �  f     ��   �  � � � l     ��������  ��  ��   �  � � � i   - 0 � � � I     ������
�� .miscidlenmbr    ��� null��  ��   � k     
 � �  � � � l     �� � ���   � W Q This is executed periodically when the script is run as a stay-open application.    � � � � �   T h i s   i s   e x e c u t e d   p e r i o d i c a l l y   w h e n   t h e   s c r i p t   i s   r u n   a s   a   s t a y - o p e n   a p p l i c a t i o n . �  � � � n     � � � I    �������� $0 doremotetraining doRemoteTraining��  ��   �  f      �  ��� � l   
 � � � � L    
 � � ]    	 � � � m    ���� < � m    ����  �   Run again in 5 minutes.    � � � � 0   R u n   a g a i n   i n   5   m i n u t e s .��   �  � � � l     ��������  ��  ��   �  � � � i   1 4 � � � I      �������� 00 shoulddisableonthismac shouldDisableOnThisMac��  ��   � k     5 � �  � � � r      � � � n     � � � I    ��~�}� $0 hostnamefordrone hostNameForDrone�~  �}   �  f      � o      �|�| 0 
_dronehost 
_droneHost �  � � � Z    �{�z  =    o    	�y�y 0 
_dronehost 
_droneHost m   	 
 �   L     m    �x
�x boovfals�{  �z   �  r    	
	 I   �w�v
�w .sysoexecTEXT���     TEXT m     � " / u s r / b i n / u n a m e   - n�v  
 o      �u�u 0 _currenthost _currentHost  Z   )�t�s =     o    �r�r 0 
_dronehost 
_droneHost o    �q�q 0 _currenthost _currentHost L   # % m   # $�p
�p boovfals�t  �s    n  * 2 I   + 2�o�n�o 0 debuglog debugLog �m b   + . m   + , � 0 D r o n e   d i s a b l e d   o n   h o s t :   o   , -�l�l 0 _currenthost _currentHost�m  �n    f   * + �k L   3 5   m   3 4�j
�j boovtrue�k   � !"! l     �i�h�g�i  �h  �g  " #$# w      %&% i   5 8'(' I     �f)�e
�f .emalcpmanull���     ****) o      �d�d 0 	_messages  �e  ( k     ** +,+ l     �c-.�c  - 0 * This is executed when Mail runs the rule.   . �// T   T h i s   i s   e x e c u t e d   w h e n   M a i l   r u n s   t h e   r u l e ., 0�b0 n    121 I    �a�`�_�a $0 doremotetraining doRemoteTraining�`  �_  2  f     �b  &�                                                                                  emal  alis    (  Macintosh HD               �_�BD ����Mail.app                                                       �����_�        ����  
 cu             Applications  /:System:Applications:Mail.app/     M a i l . a p p    M a c i n t o s h   H D  System/Applications/Mail.app  / ��  $ 343 l     �^�]�\�^  �]  �\  4 565 i   9 <787 I      �[�Z�Y�[ $0 doremotetraining doRemoteTraining�Z  �Y  8 k     �99 :;: Z    <=�X�W< >    >?> n     @A@ 1    �V
�V 
prunA m     BB�                                                                                  emal  alis    (  Macintosh HD               �_�BD ����Mail.app                                                       �����_�        ����  
 cu             Applications  /:System:Applications:Mail.app/     M a i l . a p p    M a c i n t o s h   H D  System/Applications/Mail.app  / ��  ? m    �U
�U boovtrue= L    
�T�T  �X  �W  ; CDC Z   EF�S�RE n   GHG I    �Q�P�O�Q 00 shoulddisableonthismac shouldDisableOnThisMac�P  �O  H  f    F L    �N�N  �S  �R  D IJI O    .KLK r   " -MNM I  " +�M�LO
�M .mtSSLokSnull��� ��� null�L  O �KPQ
�K 
SKeyP m   $ %RR �SS . A p p l e M a i l U s e J u n k M a i l b o xQ �JT�I
�J 
ValuT m   & '�H
�H boovfals�I  N o      �G�G  0 usejunkmailbox useJunkMailboxL m    UU�                                                                                  mtSS  alis    .  Macintosh HD               �_�BD ����SpamSieve.app                                                  ������        ����  
 cu             Applications  /:Applications:SpamSieve.app/     S p a m S i e v e . a p p    M a c i n t o s h   H D  Applications/SpamSieve.app  / ��  J VWV Q   / XXYZX O  2 ;[\[ e   6 :]] 1   6 :�F
�F 
vers\ m   2 3^^�                                                                                  emal  alis    (  Macintosh HD               �_�BD ����Mail.app                                                       �����_�        ����  
 cu             Applications  /:System:Applications:Mail.app/     M a i l . a p p    M a c i n t o s h   H D  System/Applications/Mail.app  / ��  Y R      �E_`
�E .ascrerr ****      � ****_ o      �D�D 
0 _error  ` �Ca�B
�C 
errna o      �A�A 0 _errornumber _errorNumber�B  Z Z   C Xbc�@�?b =  C Fded o   C D�>�> 0 _errornumber _errorNumbere m   D E�=�=�1c l  I Tfghf k   I Tii jkj r   I Llml m   I Jnn �oo� Y o u   c a n   g i v e    A p p l e   M a i l   -   R e m o t e   T r a i n i n g    a c c e s s   t o   c o n t r o l   M a i l   a n d   S p a m S i e v e   f r o m   S y s t e m   P r e f e r e n c e s   >   S e c u r i t y   &   P r i v a c y   >   P r i v a c y   >   A u t o m a t i o n .   F o r   m o r e   i n f o r m a t i o n ,   p l e a s e   s e e : 
 
 h t t p s : / / c - c o m m a n d . c o m / s p a m s i e v e / h e l p / s e c u r i t y - p r i v a c y - a c c em o      �<�< 0 _alertmessage _alertMessagek p�;p I  M T�:qr
�: .sysodisAaleR        TEXTq o   M N�9�9 
0 _error  r �8s�7
�8 
mesSs o   O P�6�6 0 _alertmessage _alertMessage�7  �;  g   errAEEventNotPermitted   h �tt .   e r r A E E v e n t N o t P e r m i t t e d�@  �?  W u�5u O   Y �vwv k   ] �xx yzy r   ] d{|{ n  ] b}~} I   ^ b�4�3�2�4 "0 accountstocheck accountsToCheck�3  �2  ~  f   ] ^| o      �1�1 0 	_accounts  z �0 X   e ���/�� k   y ��� ��� n  y ���� I   z ��.��-�. 0 debuglog debugLog� ��,� b   z ���� m   z }�� ��� $ C h e c k i n g   a c c o u n t :  � n  } ���� 1   ~ ��+
�+ 
pnam� o   } ~�*�* 0 _account  �,  �-  �  f   y z� ��)� Q   � ����� n  � ���� I   � ��(��'�( 00 trainmessagesinaccount trainMessagesInAccount� ��&� o   � ��%�% 0 _account  �&  �'  �  f   � �� R      �$��#
�$ .ascrerr ****      � ****� o      �"�" 
0 _error  �#  � n  � ���� I   � ��!�� �! 0 logtoconsole logToConsole� ��� b   � ���� b   � ���� b   � ���� m   � ��� ��� : E r r o r   t r a i n i n g   f r o m   a c c o u n t   � n  � ���� 1   � ��
� 
pnam� o   � ��� 0 _account  � m   � ��� ���   :  � o   � ��� 
0 _error  �  �   �  f   � ��)  �/ 0 _account  � o   h i�� 0 	_accounts  �0  w m   Y Z���                                                                                  emal  alis    (  Macintosh HD               �_�BD ����Mail.app                                                       �����_�        ����  
 cu             Applications  /:System:Applications:Mail.app/     M a i l . a p p    M a c i n t o s h   H D  System/Applications/Mail.app  / ��  �5  6 ��� l     ����  �  �  � ��� i   = @��� I      ���� "0 accountstocheck accountsToCheck�  �  � O     r��� k    q�� ��� r    ��� J    ��  � o      �� 0 _result  � ��� Z   	 n����� o   	 
��  0 usejunkmailbox useJunkMailbox� X    G���� Q    B���� Z   " 9����� n  " &��� 1   # %�
� 
isac� o   " #�� 0 _account  � k   ) 5�� ��� n  ) 0��� I   * 0���
� 0 findmailbox findMailbox� ��� m   * +�� ���  T r a i n S p a m� ��	� o   + ,�� 0 _account  �	  �
  �  f   ) *� ��� s   1 5��� o   1 2�� 0 _account  � n      ���  ;   3 4� o   2 3�� 0 _result  �  �  �  � R      ���
� .ascrerr ****      � ****�  �  � l  A A����  � , & Avoid creating a mailbox                � ��� L   A v o i d   c r e a t i n g   a   m a i l b o x                          � 0 _account  � 2   � 
�  
mact�  � X   J n����� k   ^ i�� ��� r   ^ d��� 4   ^ b���
�� 
mact� o   ` a���� 0 _accountname _accountName� o      ���� 0 _account  � ���� s   e i��� o   e f���� 0 _account  � n      ���  ;   g h� o   f g���� 0 _result  ��  �� 0 _accountname _accountName� n  M R��� I   N R�������� ,0 accountnamesfordrone accountNamesForDrone��  ��  �  f   M N� ���� L   o q�� o   o p���� 0 _result  ��  � m     ���                                                                                  emal  alis    (  Macintosh HD               �_�BD ����Mail.app                                                       �����_�        ����  
 cu             Applications  /:System:Applications:Mail.app/     M a i l . a p p    M a c i n t o s h   H D  System/Applications/Mail.app  / ��  � ��� l     ��������  ��  ��  � ��� i   A D��� I      ������� 00 trainmessagesinaccount trainMessagesInAccount� ���� o      ���� 0 _account  ��  ��  � O    ��� k   �� ��� r    ��� n   ��� I    ������� *0 messagesfrommailbox messagesFromMailbox� ��� m    �� ���  T r a i n S p a m� ���� o    ���� 0 _account  ��  ��  �  f    � o      ���� 0 	_messages  �    X    ��� k    }  r    & n   $	
	 I    $������ &0 sourcefrommessage sourceFromMessage �� o     ���� 0 _message  ��  ��  
  f     o      ���� 0 _source    O  ' 3 I  + 2����
�� .mtSSaddSnull��� ��� null��   ����
�� 
Mess o   - .���� 0 _source  ��   m   ' (�                                                                                  mtSS  alis    .  Macintosh HD               �_�BD ����SpamSieve.app                                                  ������        ����  
 cu             Applications  /:Applications:SpamSieve.app/     S p a m S i e v e . a p p    M a c i n t o s h   H D  Applications/SpamSieve.app  / ��    r   4 9 m   4 5��
�� boovtrue n      1   6 8��
�� 
isjk o   5 6���� 0 _message    Z   : K���� o   : ?���� (0 pcolorspammessages pColorSpamMessages r   B G m   B C��
�� qqclccbl n      !  1   D F��
�� 
mcol! o   C D���� 0 _message  ��  ��   "#" Z   L ]$%����$ o   L Q���� &0 pflagspammessages pFlagSpamMessages% r   T Y&'& m   T U���� ' n     ()( 1   V X��
�� 
fidx) o   U V���� 0 _message  ��  ��  # *+* Z   ^ o,-����, o   ^ c���� .0 pmarkspammessagesread pMarkSpamMessagesRead- r   f k./. m   f g��
�� boovtrue/ n     010 1   h j��
�� 
isrd1 o   g h���� 0 _message  ��  ��  + 2��2 n  p }343 I   q }��5���� 0 movemessage moveMessage5 676 o   q r���� 0 _message  7 898 n  r x:;: I   s x��<���� .0 spammailboxforaccount spamMailboxForAccount< =��= o   s t���� 0 _account  ��  ��  ;  f   r s9 >��> m   x y��
�� boovtrue��  ��  4  f   p q��  �� 0 _message   o    ���� 0 	_messages   ?@? l  � ���������  ��  ��  @ ABA r   � �CDC n  � �EFE I   � ���G���� *0 messagesfrommailbox messagesFromMailboxG HIH m   � �JJ �KK  T r a i n G o o dI L��L o   � ����� 0 _account  ��  ��  F  f   � �D o      ���� 0 	_messages  B M��M X   �N��ON k   � PP QRQ r   � �STS n  � �UVU I   � ���W���� &0 sourcefrommessage sourceFromMessageW X��X o   � ����� 0 _message  ��  ��  V  f   � �T o      ���� 0 _source  R YZY O  � �[\[ I  � �����]
�� .mtSSaddGnull��� ��� null��  ] ��^��
�� 
Mess^ o   � ����� 0 _source  ��  \ m   � �__�                                                                                  mtSS  alis    .  Macintosh HD               �_�BD ����SpamSieve.app                                                  ������        ����  
 cu             Applications  /:Applications:SpamSieve.app/     S p a m S i e v e . a p p    M a c i n t o s h   H D  Applications/SpamSieve.app  / ��  Z `a` r   � �bcb m   � ���
�� boovfalsc n     ded 1   � ���
�� 
isjke o   � ����� 0 _message  a fgf Z   � �hi����h o   � ����� (0 pcolorspammessages pColorSpamMessagesi r   � �jkj m   � ���
�� exutccnok n     lml 1   � ���
�� 
mcolm o   � ����� 0 _message  ��  ��  g non Z   � �pq����p o   � ����� &0 pflagspammessages pFlagSpamMessagesq r   � �rsr m   � �������s n     tut 1   � ���
�� 
fidxu o   � ����� 0 _message  ��  ��  o vwv Z   � �xy����x o   � ����� 20 pmarkgoodmessagesunread pMarkGoodMessagesUnready r   � �z{z m   � ���
�� boovfals{ n     |}| 1   � ���
�� 
isrd} o   � ����� 0 _message  ��  ��  w ~��~ n  � � I   � ������� 0 movemessage moveMessage� ��� o   � ����� 0 _message  � ��� n  � ���� I   � �������� "0 inboxforaccount inboxForAccount� ���� o   � ����� 0 _account  ��  ��  �  f   � �� ���� m   � ���
�� boovfals��  ��  �  f   � ���  �� 0 _message  O o   � ����� 0 	_messages  ��  � m     ���                                                                                  emal  alis    (  Macintosh HD               �_�BD ����Mail.app                                                       �����_�        ����  
 cu             Applications  /:System:Applications:Mail.app/     M a i l . a p p    M a c i n t o s h   H D  System/Applications/Mail.app  / ��  � ��� l     ��������  ��  ��  � ��� i   E H��� I      ������� *0 messagesfrommailbox messagesFromMailbox� ��� o      ���� 0 _mailboxname _mailboxName� ���� o      ���� 0 _account  ��  ��  � O     t��� k    s�� ��� r    	��� n    ��� 1    ��
�� 
pnam� o    �� 0 _account  � o      �~�~ 0 _accountname _accountName� ��� Q   
 6���� r    ��� n   ��� I    �}��|�} 0 findmailbox findMailbox� ��� o    �{�{ 0 _mailboxname _mailboxName� ��z� o    �y�y 0 _account  �z  �|  �  f    � o      �x�x 0 _mailbox  � R      �w�v�u
�w .ascrerr ****      � ****�v  �u  � k    6�� ��� O    /��� I  " .�t�s�
�t .corecrel****      � null�s  � �r��
�r 
kocl� m   $ %�q
�q 
mbxp� �p��o
�p 
prdt� K   & *�� �n��m
�n 
pnam� o   ' (�l�l 0 _mailboxname _mailboxName�m  �o  � o    �k�k 0 _account  � ��j� r   0 6��� n   0 4��� 4   1 4�i�
�i 
mbxp� o   2 3�h�h 0 _mailboxname _mailboxName� o   0 1�g�g 0 _account  � o      �f�f 0 _mailbox  �j  � ��� n  7 D��� I   8 D�e��d�e 0 debuglog debugLog� ��c� n  8 @��� I   9 @�b��a�b  0 makelogmessage makeLogMessage� ��� m   9 :�� ��� 6 G e t t i n g   m e s s a g e s   i n   m a i l b o x� ��� o   : ;�`�` 0 _mailbox  � ��_� m   ; <�� ��� j T h i s   c a n   t a k e   a   l o n g   t i m e   i f   t h e r e   a r e   m a n y   m e s s a g e s .�_  �a  �  f   8 9�c  �d  �  f   7 8� ��� t   E \��� r   I [��� 6  I Y��� n   I L��� 2  J L�^
�^ 
mssg� o   I J�]�] 0 _mailbox  � =  O X��� 1   P T�\
�\ 
isdl� m   U W�[
�[ boovfals� o      �Z�Z 0 	_messages  � ]   E H��� m   E F�Y�Y � m   F G�X�X <� ��� n  ] p��� I   ^ p�W��V�W 0 debuglog debugLog� ��U� n  ^ l��� I   _ l�T��S�T  0 makelogmessage makeLogMessage� ��� m   _ b�� ��� & M e s s a g e s   i n   m a i l b o x� ��� o   b c�R�R 0 _mailbox  � ��Q� I  c h�P��O
�P .corecnte****       ****� o   c d�N�N 0 	_messages  �O  �Q  �S  �  f   ^ _�U  �V  �  f   ] ^� ��M� L   q s�� o   q r�L�L 0 	_messages  �M  � m     ���                                                                                  emal  alis    (  Macintosh HD               �_�BD ����Mail.app                                                       �����_�        ����  
 cu             Applications  /:System:Applications:Mail.app/     M a i l . a p p    M a c i n t o s h   H D  System/Applications/Mail.app  / ��  � ��� l     �K�J�I�K  �J  �I  � ��� i   I L��� I      �H��G�H 0 findmailbox findMailbox� ��� o      �F�F 0 _mailboxname _mailboxName� ��E� o      �D�D 0 _account  �E  �G  � O     S��� Q    R���� L       n     4    �C
�C 
mbxp o   	 
�B�B 0 _mailboxname _mailboxName o    �A�A 0 _account  � R      �@�?�>
�@ .ascrerr ****      � ****�?  �>  � k    R  l   �=�=   c ] my debugLog("Looking for nested mailbox " & _mailboxName & " in account " & _account's name)    �		 �   m y   d e b u g L o g ( " L o o k i n g   f o r   n e s t e d   m a i l b o x   "   &   _ m a i l b o x N a m e   &   "   i n   a c c o u n t   "   &   _ a c c o u n t ' s   n a m e ) 

 r      n    I    �<�;�< &0 findnestedmailbox findNestedMailbox  o    �:�: 0 _mailboxname _mailboxName �9 n     2   �8
�8 
mbxp o    �7�7 0 _account  �9  �;    f     o      �6�6 0 _result    Z   ! <�5�4 >  ! $ o   ! "�3�3 0 _result   m   " #�2
�2 
msng k   ' 8  n  ' 5  I   ( 5�1!�0�1 0 debuglog debugLog! "�/" b   ( 1#$# b   ( -%&% b   ( +'(' m   ( ))) �** * F o u n d   n e s t e d   m a i l b o x  ( o   ) *�.�. 0 _mailboxname _mailboxName& m   + ,++ �,,    i n   a c c o u n t  $ n  - 0-.- 1   . 0�-
�- 
pnam. o   - .�,�, 0 _account  �/  �0     f   ' ( /�+/ L   6 800 o   6 7�*�* 0 _result  �+  �5  �4   121 n  = K343 I   > K�)5�(�) 0 debuglog debugLog5 6�'6 b   > G787 b   > C9:9 b   > A;<; m   > ?== �>> $ N o   n e s t e d   m a i l b o x  < o   ? @�&�& 0 _mailboxname _mailboxName: m   A B?? �@@    i n   a c c o u n t  8 n  C FABA 1   D F�%
�% 
pnamB o   C D�$�$ 0 _account  �'  �(  4  f   = >2 C�#C R   L R�"D�!
�" .ascrerr ****      � ****D b   N QEFE m   N OGG �HH " N o   m a i l b o x   n a m e d  F o   O P� �  0 _mailboxname _mailboxName�!  �#  � m     II�                                                                                  emal  alis    (  Macintosh HD               �_�BD ����Mail.app                                                       �����_�        ����  
 cu             Applications  /:System:Applications:Mail.app/     M a i l . a p p    M a c i n t o s h   H D  System/Applications/Mail.app  / ��  � JKJ l     ����  �  �  K LML i   M PNON I      �P�� &0 findnestedmailbox findNestedMailboxP QRQ o      �� 0 _mailboxname _mailboxNameR S�S o      �� 0 
_mailboxes  �  �  O O     YTUT k    XVV WXW X    'Y�ZY Z    "[\��[ =   ]^] n    _`_ 1    �
� 
pnam` o    �� 0 _mailbox  ^ o    �� 0 _mailboxname _mailboxName\ L    aa o    �� 0 _mailbox  �  �  � 0 _mailbox  Z o    �� 0 
_mailboxes  X bcb X   ( Ud�ed k   8 Pff ghg r   8 Ciji n  8 Aklk I   9 A�m�� &0 findnestedmailbox findNestedMailboxm non o   9 :�� 0 _mailboxname _mailboxNameo p�p n   : =qrq 2  ; =�

�
 
mbxpr o   : ;�	�	 0 _mailbox  �  �  l  f   8 9j o      �� 0 _result  h s�s Z   D Ptu��t >  D Gvwv o   D E�� 0 _result  w m   E F�
� 
msngu L   J Lxx o   J K�� 0 _result  �  �  �  � 0 _mailbox  e o   + ,�� 0 
_mailboxes  c y� y L   V Xzz m   V W��
�� 
msng�   U m     {{�                                                                                  emal  alis    (  Macintosh HD               �_�BD ����Mail.app                                                       �����_�        ����  
 cu             Applications  /:System:Applications:Mail.app/     M a i l . a p p    M a c i n t o s h   H D  System/Applications/Mail.app  / ��  M |}| l     ��������  ��  ��  } ~~ i   Q T��� I      ������� &0 sourcefrommessage sourceFromMessage� ���� o      ���� 0 _message  ��  ��  � O     ��� k    �� ��� n   ��� I    ������� 0 debuglog debugLog� ���� n   ��� I    �������  0 makelogmessage makeLogMessage� ��� m    �� ��� 8 G e t t i n g   s o u r c e   o f   m e s s a g e   i n� ��� n   
��� m    
��
�� 
mbxp� o    ���� 0 _message  � ���� n  
 ��� 1    ��
�� 
subj� o   
 ���� 0 _message  ��  ��  �  f    ��  ��  �  f    � ���� L    �� n   ��� 1    ��
�� 
raso� o    ���� 0 _message  ��  � m     ���                                                                                  emal  alis    (  Macintosh HD               �_�BD ����Mail.app                                                       �����_�        ����  
 cu             Applications  /:System:Applications:Mail.app/     M a i l . a p p    M a c i n t o s h   H D  System/Applications/Mail.app  / ��   ��� l     ��������  ��  ��  � ��� i   U X��� I      ������� 0 movemessage moveMessage� ��� o      ���� 0 _message  � ��� o      ���� 0 _mailbox  � ���� o      ���� 0 _isspam _isSpam��  ��  � O     v��� k    u�� ��� Z    %������� H    �� o    ����  0 usejunkmailbox useJunkMailbox� k   	 !�� ��� n  	 ��� I   
 ������� 0 debuglog debugLog� ���� n  
 ��� I    �������  0 makelogmessage makeLogMessage� ��� m    �� ��� " M o v i n g   m e s s a g e   t o� ��� o    ���� 0 _mailbox  � ���� n   ��� 1    ��
�� 
subj� o    ���� 0 _message  ��  ��  �  f   
 ��  ��  �  f   	 
� ��� r    ��� o    ���� 0 _mailbox  � n     ��� m    ��
�� 
mbxp� o    ���� 0 _message  � ���� L    !����  ��  ��  ��  � ���� Z   & u������ o   & '���� 0 _isspam _isSpam� k   * >�� ��� n  * 4��� I   + 4������� 0 debuglog debugLog� ���� b   + 0��� m   + ,�� ��� 0 M o v i n g   m e s s a g e   t o   J u n k :  � n  , /��� 1   - /��
�� 
subj� o   , -���� 0 _message  ��  ��  �  f   * +� ���� I  5 >����
�� .coremovenull���     obj � o   5 6���� 0 _message  � �����
�� 
insh� 1   7 :��
�� 
jkmb��  ��  ��  � Z   A u������ o   A F���� .0 pmovebysettingmailbox pMoveBySettingMailbox� k   I ^�� ��� n  I X��� I   J X������� 0 debuglog debugLog� ���� n  J T��� I   K T�������  0 makelogmessage makeLogMessage� ��� m   K L�� ��� " M o v i n g   m e s s a g e   t o� ��� o   L M���� 0 _mailbox  � ���� n  M P��� 1   N P��
�� 
subj� o   M N���� 0 _message  ��  ��  �  f   J K��  ��  �  f   I J� ���� r   Y ^��� o   Y Z���� 0 _mailbox  � n     ��� m   [ ]��
�� 
mbxp� o   Z [���� 0 _message  ��  ��  � k   a u�� � � l  a a����   � � Not used by default because for many users copies rather than moves messages that Mail reports are in Gmail's All Mail, however some users report that this works better (#kZMU4ZD8QOzpruuManwLChA).    ��   N o t   u s e d   b y   d e f a u l t   b e c a u s e   f o r   m a n y   u s e r s   c o p i e s   r a t h e r   t h a n   m o v e s   m e s s a g e s   t h a t   M a i l   r e p o r t s   a r e   i n   G m a i l ' s   A l l   M a i l ,   h o w e v e r   s o m e   u s e r s   r e p o r t   t h a t   t h i s   w o r k s   b e t t e r   ( # k Z M U 4 Z D 8 Q O z p r u u M a n w L C h A ) .   n  a k I   b k������ 0 debuglog debugLog 	��	 b   b g

 m   b c � 2 M o v i n g   m e s s a g e   t o   I n b o x :   n  c f 1   d f��
�� 
subj o   c d���� 0 _message  ��  ��    f   a b �� I  l u��
�� .coremovenull���     obj  o   l m���� 0 _message   ����
�� 
insh 1   n q��
�� 
inmb��  ��  ��  � m     �                                                                                  emal  alis    (  Macintosh HD               �_�BD ����Mail.app                                                       �����_�        ����  
 cu             Applications  /:System:Applications:Mail.app/     M a i l . a p p    M a c i n t o s h   H D  System/Applications/Mail.app  / ��  �  l     ��������  ��  ��    i   Y \ I      ������  0 makelogmessage makeLogMessage  o      ���� 0 _action    o      ���� 0 _mailbox    ��  o      ���� 0 _detail  ��  ��   L     !! b     "#" b     $%$ b     
&'& b     ()( o     ���� 0 _action  ) m    ** �++   ' n   	,-, I    	��.���� "0 describemailbox describeMailbox. /��/ o    ���� 0 _mailbox  ��  ��  -  f    % m   
 00 �11  :  # o    ���� 0 _detail   232 l     ��������  ��  ��  3 454 i   ] `676 I      ��8���� "0 describemailbox describeMailbox8 9��9 o      ���� 0 _mailbox  ��  ��  7 O     +:;: k    *<< =>= r    	?@? n   ABA 1    ��
�� 
pnamB o    ���� 0 _mailbox  @ o      ���� 0 _mailboxname _mailboxName> CDC Q   
 EFGE r    HIH n    JKJ 1    ��
�� 
pnamK n   LML m    ��
�� 
mactM o    ���� 0 _mailbox  I o      ���� 0 _accountname _accountNameF R      ������
�� .ascrerr ****      � ****��  ��  G r    NON m    PP �QQ  O n   M y   M a cO o      ���� 0 _accountname _accountNameD R��R L     *SS b     )TUT b     'VWV b     %XYX b     #Z[Z m     !\\ �]]  [ o   ! "���� 0 _accountname _accountNameY m   # $^^ �__ 
    /   W o   % &���� 0 _mailboxname _mailboxNameU m   ' (`` �aa  ��  ; m     bb�                                                                                  emal  alis    (  Macintosh HD               �_�BD ����Mail.app                                                       �����_�        ����  
 cu             Applications  /:System:Applications:Mail.app/     M a i l . a p p    M a c i n t o s h   H D  System/Applications/Mail.app  / ��  5 cdc l     ��������  ��  ��  d efe i   a dghg I      ��i��� .0 spammailboxforaccount spamMailboxForAccounti j�~j o      �}�} 0 _account  �~  �  h k     Pkk lml Z    
no�|�{n o     �z�z  0 usejunkmailbox useJunkMailboxo L    pp m    �y
�y 
msng�|  �{  m q�xq O    Prsr k    Ott uvu X    Dw�wxw Z   # ?yz�v�uy =  # +{|{ n   # '}~} 4   $ '�t
�t 
cobj m   % &�s�s ~ o   # $�r�r 	0 _pair  | n   ' *��� 1   ( *�q
�q 
pnam� o   ' (�p�p 0 _account  z k   . ;�� ��� r   . 4��� n   . 2��� 4   / 2�o�
�o 
cobj� m   0 1�n�n � o   . /�m�m 	0 _pair  � o      �l�l 	0 _name  � ��k� L   5 ;�� n   5 :��� 4   6 9�j�
�j 
mbxp� o   7 8�i�i 	0 _name  � o   5 6�h�h 0 _account  �k  �v  �u  �w 	0 _pair  x n   ��� I    �g�f�e�g 60 spammailboxnamesbyaccount spamMailboxNamesByAccount�f  �e  �  f    v ��d� L   E O�� n   E N��� 4   F M�c�
�c 
mbxp� o   G L�b�b $0 pspammailboxname pSpamMailboxName� o   E F�a�a 0 _account  �d  s m    ���                                                                                  emal  alis    (  Macintosh HD               �_�BD ����Mail.app                                                       �����_�        ����  
 cu             Applications  /:System:Applications:Mail.app/     M a i l . a p p    M a c i n t o s h   H D  System/Applications/Mail.app  / ��  �x  f ��� l     �`�_�^�`  �_  �^  � ��� i   e h��� I      �]��\�] "0 inboxforaccount inboxForAccount� ��[� o      �Z�Z 0 _account  �[  �\  � O     @��� k    ?�� ��� r    ��� J    �� ��� m    �� ���  I s G o o d� ��� m    �� ��� 
 I N B O X� ��� m    �� ��� 
 I n b o x� ��� m    �� ���  i n n b o k s� ��� m    	�� ���  P o s t e i n g a n g� ��Y� m   	 
�� ��� $ B o i t e   d e   r e c e p t i o n�Y  � o      �X�X 
0 _names  � ��� X    9��W�� Q    4���V� k   " +�� ��� r   " (��� n   " &��� 4   # &�U�
�U 
mbxp� o   $ %�T�T 	0 _name  � o   " #�S�S 0 _account  � o      �R�R 0 _mailbox  � ��Q� L   ) +�� o   ) *�P�P 0 _mailbox  �Q  � R      �O�N�M
�O .ascrerr ****      � ****�N  �M  �V  �W 	0 _name  � o    �L�L 
0 _names  � ��K� L   : ?�� 1   : >�J
�J 
inmb�K  � m     ���                                                                                  emal  alis    (  Macintosh HD               �_�BD ����Mail.app                                                       �����_�        ����  
 cu             Applications  /:System:Applications:Mail.app/     M a i l . a p p    M a c i n t o s h   H D  System/Applications/Mail.app  / ��  � ��� l     �I�H�G�I  �H  �G  � ��� i   i l��� I      �F��E�F  0 lookupdefaults lookupDefaults� ��� o      �D�D 	0 _keys  � ��C� o      �B�B  0 _defaultvalues _defaultValues�C  �E  � O     S��� Q    R���� k    @�� ��� r    ��� J    	�A�A  � o      �@�@ 0 _result  � ��� Y    =��?���>� k    8�� ��� r     ��� n    ��� 4    �=�
�= 
cobj� o    �<�< 0 _i  � o    �;�; 	0 _keys  � o      �:�: 0 _key  � ��� r   ! '��� n   ! %��� 4   " %�9�
�9 
cobj� o   # $�8�8 0 _i  � o   ! "�7�7  0 _defaultvalues _defaultValues� o      �6�6 0 _defaultvalue _defaultValue� ��� r   ( 3��� I  ( 1�5�4�
�5 .mtSSLokSnull��� ��� null�4  � �3��
�3 
SKey� o   * +�2�2 0 _key  � �1 �0
�1 
Valu  o   , -�/�/ 0 _defaultvalue _defaultValue�0  � o      �.�. 
0 _value  � �- s   4 8 o   4 5�,�, 
0 _value   n        ;   6 7 o   5 6�+�+ 0 _result  �-  �? 0 _i  � m    �*�* � I   �)�(
�) .corecnte****       **** o    �'�' 	0 _keys  �(  �>  � �& L   > @ o   > ?�%�% 0 _result  �&  � R      �$�#�"
�$ .ascrerr ****      � ****�#  �"  � l  H R	
	 L   H R I  H Q�!� 
�! .mtSSLooknull��� ��� null�    �
� 
Keys o   J K�� 	0 _keys   ��
� 
Vals o   L M��  0 _defaultvalues _defaultValues�  
 #  SpamSieve 2.9.15 and earlier    � :   S p a m S i e v e   2 . 9 . 1 5   a n d   e a r l i e r� m     �                                                                                  mtSS  alis    .  Macintosh HD               �_�BD ����SpamSieve.app                                                  ������        ����  
 cu             Applications  /:Applications:SpamSieve.app/     S p a m S i e v e . a p p    M a c i n t o s h   H D  Applications/SpamSieve.app  / ��  � � l     ����  �  �  �       ������ ;� !"#$%&'()*�   ������
�	��������� ��������������������������� .0 pmarkspammessagesread pMarkSpamMessagesRead� (0 pcolorspammessages pColorSpamMessages� &0 pflagspammessages pFlagSpamMessages� 20 pmarkgoodmessagesunread pMarkGoodMessagesUnread� .0 pmovebysettingmailbox pMoveBySettingMailbox�
 $0 pspammailboxname pSpamMailboxName�	 *0 penabledebuglogging pEnableDebugLogging� ,0 accountnamesfordrone accountNamesForDrone� 60 spammailboxnamesbyaccount spamMailboxNamesByAccount� $0 hostnamefordrone hostNameForDrone� 0 debuglog debugLog� 0 logtoconsole logToConsole
� .aevtoappnull  �   � ****
� .miscidlenmbr    ��� null� 00 shoulddisableonthismac shouldDisableOnThisMac
�  .emalcpmanull���     ****�� $0 doremotetraining doRemoteTraining�� "0 accountstocheck accountsToCheck�� 00 trainmessagesinaccount trainMessagesInAccount�� *0 messagesfrommailbox messagesFromMailbox�� 0 findmailbox findMailbox�� &0 findnestedmailbox findNestedMailbox�� &0 sourcefrommessage sourceFromMessage�� 0 movemessage moveMessage��  0 makelogmessage makeLogMessage�� "0 describemailbox describeMailbox�� .0 spammailboxforaccount spamMailboxForAccount�� "0 inboxforaccount inboxForAccount��  0 lookupdefaults lookupDefaults
� boovfals
� boovtrue
� boovfals
� boovfals
� boovtrue
� boovfals �� H����+,���� ,0 accountnamesfordrone accountNamesForDrone��  ��  +  ,  X�� �kv �� _����-.���� 60 spammailboxnamesbyaccount spamMailboxNamesByAccount��  ��  -  .  �� jv �� w����/0���� $0 hostnamefordrone hostNameForDrone��  ��  / ���� 	0 _host  0  | � �������  0 lookupdefaults lookupDefaults
�� 
cobj�� �O)�kv�kvl+ E[�k/E�ZO� �� �����12���� 0 debuglog debugLog�� ��3�� 3  ���� 0 _message  ��  1 ���� 0 _message  2 ���� 0 logtoconsole logToConsole�� b   )�k+  Y h �� �����45���� 0 logtoconsole logToConsole�� ��6�� 6  ���� 0 _message  ��  4 ������ 0 _message  �� 0 _logmessage _logMessage5  � �����
�� 
strq
�� .sysoexecTEXT���     TEXT�� �%E�O��,%j  �� �����78��
�� .aevtoappnull  �   � ****��  ��  7  8 ���� $0 doremotetraining doRemoteTraining�� )j+   �� �����9:��
�� .miscidlenmbr    ��� null��  ��  9  : �������� $0 doremotetraining doRemoteTraining�� <�� �� )j+  O��  �� �����;<���� 00 shoulddisableonthismac shouldDisableOnThisMac��  ��  ; ������ 0 
_dronehost 
_droneHost�� 0 _currenthost _currentHost< �������� $0 hostnamefordrone hostNameForDrone
�� .sysoexecTEXT���     TEXT�� 0 debuglog debugLog�� 6)j+  E�O��  fY hO�j E�O��  fY hO)�%k+ Oe ��(����=>��
�� .emalcpmanull���     ****�� 0 	_messages  ��  = ���� 0 	_messages  > ���� $0 doremotetraining doRemoteTraining�� )j+   ��8����?@���� $0 doremotetraining doRemoteTraining��  ��  ? ������������ 
0 _error  �� 0 _errornumber _errorNumber�� 0 _alertmessage _alertMessage�� 0 	_accounts  �� 0 _account  @ B����U��R������������A��n�������������������������
�� 
prun�� 00 shoulddisableonthismac shouldDisableOnThisMac
�� 
SKey
�� 
Valu�� 
�� .mtSSLokSnull��� ��� null��  0 usejunkmailbox useJunkMailbox
�� 
vers�� 
0 _error  A ������
�� 
errn�� 0 _errornumber _errorNumber��  ���1
�� 
mesS
�� .sysodisAaleR        TEXT�� "0 accountstocheck accountsToCheck
�� 
kocl
�� 
cobj
�� .corecnte****       ****
�� 
pnam�� 0 debuglog debugLog�� 00 trainmessagesinaccount trainMessagesInAccount��  �� 0 logtoconsole logToConsole�� ���,e hY hO)j+  hY hO� *���f� E�UO � *�,EUW X  ��  �E�O��l Y hO� W)j+ E�O L�[a a l kh )a �a ,%k+ O )�k+ W X  )a �a ,%a %�%k+ [OY��U �������BC���� "0 accountstocheck accountsToCheck��  ��  B �������� 0 _result  �� 0 _account  �� 0 _accountname _accountNameC ������������������������  0 usejunkmailbox useJunkMailbox
�� 
mact
�� 
kocl
�� 
cobj
�� .corecnte****       ****
�� 
isac�� 0 findmailbox findMailbox��  ��  �� ,0 accountnamesfordrone accountNamesForDrone�� s� ojvE�O� ? 9*�-[��l kh  ��,E )�l+ O��6GY hW X 	 
h[OY��Y & #)j+ [��l kh *�/E�O��6G[OY��O�U  �������DE���� 00 trainmessagesinaccount trainMessagesInAccount�� ��F�� F  �� 0 _account  ��  D �~�}�|�{�~ 0 _account  �} 0 	_messages  �| 0 _message  �{ 0 _source  E ���z�y�x�w�v�u�t�s�r�q�p�o�n�m�lJ�k�j�i�z *0 messagesfrommailbox messagesFromMailbox
�y 
kocl
�x 
cobj
�w .corecnte****       ****�v &0 sourcefrommessage sourceFromMessage
�u 
Mess
�t .mtSSaddSnull��� ��� null
�s 
isjk
�r qqclccbl
�q 
mcol�p 
�o 
fidx
�n 
isrd�m .0 spammailboxforaccount spamMailboxForAccount�l 0 movemessage moveMessage
�k .mtSSaddGnull��� ��� null
�j exutccno�i "0 inboxforaccount inboxForAccount���)�l+ E�O s�[��l kh )�k+ E�O� 	*�l 	UOe��,FOb   
��,FY hOb   
���,FY hOb    
e��,FY hO)�)�k+ em+ [OY��O)a �l+ E�O u�[��l kh )�k+ E�O� 	*�l UOf��,FOb   a ��,FY hOb   
i��,FY hOb   
f��,FY hO)�)�k+ fm+ [OY��U! �h��g�fGH�e�h *0 messagesfrommailbox messagesFromMailbox�g �dI�d I  �c�b�c 0 _mailboxname _mailboxName�b 0 _account  �f  G �a�`�_�^�]�a 0 _mailboxname _mailboxName�` 0 _account  �_ 0 _accountname _accountName�^ 0 _mailbox  �] 0 	_messages  H ��\�[�Z�Y�X�W�V�U�T���S�R�Q�PJ�O��N
�\ 
pnam�[ 0 findmailbox findMailbox�Z  �Y  
�X 
kocl
�W 
mbxp
�V 
prdt�U 
�T .corecrel****      � null�S  0 makelogmessage makeLogMessage�R 0 debuglog debugLog�Q <
�P 
mssgJ  
�O 
isdl
�N .corecnte****       ****�e u� q��,E�O )��l+ E�W X  � *����l� 	UO��/E�O))��m+ k+ Om� n��-a [a ,\Zf81E�oO))a ��j m+ k+ O�U" �M��L�KKL�J�M 0 findmailbox findMailbox�L �IM�I M  �H�G�H 0 _mailboxname _mailboxName�G 0 _account  �K  K �F�E�D�F 0 _mailboxname _mailboxName�E 0 _account  �D 0 _result  L I�C�B�A�@�?)+�>�==?G
�C 
mbxp�B  �A  �@ &0 findnestedmailbox findNestedMailbox
�? 
msng
�> 
pnam�= 0 debuglog debugLog�J T� P ��/EW DX  )���-l+ E�O�� )�%�%��,%k+ 	O�Y hO)�%�%��,%k+ 	O)j�%U# �<O�;�:NO�9�< &0 findnestedmailbox findNestedMailbox�; �8P�8 P  �7�6�7 0 _mailboxname _mailboxName�6 0 
_mailboxes  �:  N �5�4�3�2�5 0 _mailboxname _mailboxName�4 0 
_mailboxes  �3 0 _mailbox  �2 0 _result  O {�1�0�/�.�-�,�+
�1 
kocl
�0 
cobj
�/ .corecnte****       ****
�. 
pnam
�- 
mbxp�, &0 findnestedmailbox findNestedMailbox
�+ 
msng�9 Z� V "�[��l kh ��,�  �Y h[OY��O ,�[��l kh )���-l+ E�O�� �Y h[OY��O�U$ �*��)�(QR�'�* &0 sourcefrommessage sourceFromMessage�) �&S�& S  �%�% 0 _message  �(  Q �$�$ 0 _message  R ���#�"�!� �
�# 
mbxp
�" 
subj�!  0 makelogmessage makeLogMessage�  0 debuglog debugLog
� 
raso�' � ))��,��,m+ k+ O��,EU% ����TU�� 0 movemessage moveMessage� �V� V  ���� 0 _message  � 0 _mailbox  � 0 _isspam _isSpam�  T ���� 0 _message  � 0 _mailbox  � 0 _isspam _isSpamU �������������  0 usejunkmailbox useJunkMailbox
� 
subj�  0 makelogmessage makeLogMessage� 0 debuglog debugLog
� 
mbxp
� 
insh
� 
jkmb
� .coremovenull���     obj 
� 
inmb� w� s� ))⡠�,m+ k+ O���,FOhY hO� )��,%k+ O��*�,l 
Y 6b   ))론�,m+ k+ O���,FY )��,%k+ O��*�,l 
U& �
�	�WX��
  0 makelogmessage makeLogMessage�	 �Y� Y  ���� 0 _action  � 0 _mailbox  � 0 _detail  �  W ��� � 0 _action  � 0 _mailbox  �  0 _detail  X *��0�� "0 describemailbox describeMailbox� ��%)�k+ %�%�%' ��7����Z[���� "0 describemailbox describeMailbox�� ��\�� \  ���� 0 _mailbox  ��  Z �������� 0 _mailbox  �� 0 _mailboxname _mailboxName�� 0 _accountname _accountName[ 	b��������P\^`
�� 
pnam
�� 
mact��  ��  �� ,� (��,E�O ��,�,E�W 
X  �E�O�%�%�%�%U( ��h����]^���� .0 spammailboxforaccount spamMailboxForAccount�� ��_�� _  ���� 0 _account  ��  ] �������� 0 _account  �� 	0 _pair  �� 	0 _name  ^ 	�������������������  0 usejunkmailbox useJunkMailbox
�� 
msng�� 60 spammailboxnamesbyaccount spamMailboxNamesByAccount
�� 
kocl
�� 
cobj
�� .corecnte****       ****
�� 
pnam
�� 
mbxp�� Q� �Y hO� B 4)j+ [��l kh ��k/��,  ��l/E�O��/EY h[OY��O��b  /EU) �������`a���� "0 inboxforaccount inboxForAccount�� ��b�� b  ���� 0 _account  ��  ` ���������� 0 _account  �� 
0 _names  �� 	0 _name  �� 0 _mailbox  a ������������������������� 
�� 
kocl
�� 
cobj
�� .corecnte****       ****
�� 
mbxp��  ��  
�� 
inmb�� A� =�������vE�O )�[��l 
kh  ��/E�O�W X  h[OY��O*�,EU* �������cd����  0 lookupdefaults lookupDefaults�� ��e�� e  ������ 	0 _keys  ��  0 _defaultvalues _defaultValues��  c ���������������� 	0 _keys  ��  0 _defaultvalues _defaultValues�� 0 _result  �� 0 _i  �� 0 _key  �� 0 _defaultvalue _defaultValue�� 
0 _value  d ����������������������
�� .corecnte****       ****
�� 
cobj
�� 
SKey
�� 
Valu�� 
�� .mtSSLokSnull��� ��� null��  ��  
�� 
Keys
�� 
Vals
�� .mtSSLooknull��� ��� null�� T� P >jvE�O 0k�j kh ��/E�O��/E�O*��� E�O��6G[OY��O�W X  *��� U ascr  ��ޭ