---
autonumber-headings: false
extratags: true
extratags-back: true
filename: readme
lang: tr_TR
mathjax: false
path: 'C:\Users\ITU\AppData\Roaming\nvda\addons\screenshots\doc\tr\'
template: default
title: Ekran Yakalama Sihirbazı
toc: false
...

# Ekran yakalama sihirbazı

Bu eklenti, tüm ekranın veya nesneler, pencereler vb. gibi belirli alanların ekran görüntülerini almak için bir sihirbaz sağlar. Standart klavyelerde genellikle F12 tuşunun sağındaki üçlü grubun ilki olan _print screen_ tuşu ile etkinleştirilir. Başka bir tane kullanmayı tercih ederseniz, NVDA tercihlerinde, girdi hareketlerinde yapılandırılabilir.  

Sihirbaz çağrıldığında, odakla nesnenin etrafında sanal bir dikdörtgen oluşturulur ve aşağıdakilerle bir klavye komutları katmanı etkinleştirilir:  

### komutlar:  

* F1, temel komutları içeren bir yardım mesajı sunar; iki kez basılırsa bu belgeyi açar.  

#### dikdörtgen bilgisi

1'den 7'ye kadar olan tuşlar aşağıdaki bilgileri sağlar:  

* 1: Sol üst ve sağ alt köşelerin koordinatları.  
* 2: Dikdörtgen boyutları, yükseklik ve genişlik.  
* 3: Referans nesnesi.  
* 4: Referans nesne tarafından işgal edilen dikdörtgen alanın oranı.  
* 5: Referans nesnesinin bir bölümünün dikdörtgenin dışında olup olmadığını gösterir.  
* 6: Dikdörtgenin ön planda etkin pencerenin sınırlarını aşıp aşmadığını gösterir.  
* 7: Dikdörtgenin kapladığı ekranın oranı.  

Boşluk tuşu tüm bu bilgileri arka arkaya okur.  

#### nesne seçimi:

Referans nesnesi, ekranda her zaman dikdörtgenle sınırlanan nesnedir. İlk olarak, bu nesne sistemin odak noktası olacaktır, ancak aşağıdaki tuşlarla başka bir nesne seçilebilir:  

* Yukarı ok: geçerli nesnenin kapsayıcısını çerçeveler.  
* F: Nesneyi odakla çerçeveler.  
* N: Nesne gezgininde nesneyi çerçeveler.  
* W: Etkin pencereyi çerçeveler.  
* M: fare işaretçisinin altındaki nesneyi çerçeveler.  
* S: Tüm ekranı çerçeveler.  

Aşağı ok ile değişiklikler geri alınır.  

#### dikdörtgen boyutu:

Dikdörtgenin boyutu aşağıdaki tuşlar kullanılarak değiştirilebilir:  

* Shift + oklar ile sol üst köşe hareket ettirilir:  "
* shift + yukarı veya aşağı ok üst kenarı hareket ettirir,  
* shift + sol veya sağ ok, sol kenarı hareket ettirir.  
* Control + oklar ile sağ alt köşe hareket ettirilir:  
* kontrol + yukarı veya aşağı ok, alt kenarı hareket ettirir,  
* control + sol veya sağ ok sağ kenarı hareket ettirir.  
* control + shift + yukarı ok, dört kenarı da dışa doğru hareket ettirerek dikdörtgeni genişletir.  
* control + shift + aşağı ok, dört kenarı da içe doğru hareket ettirerek dikdörtgeni daraltır.  

Bu hareketler için piksel sayısı sayfa yukarı ve sayfa aşağı tuşları ile değiştirilebilir. Tercihlerde de aynı değişikliği yapabilirsiniz.  

Dikdörtgeni yeniden boyutlandırarak referans nesnesi değişebilir. Her zaman ortalanmış, ön planda olan ve dikdörtgen içinde daha geniş bir alanı kaplayan nesneyi seçmeye çalışacaktır. Nesne değişiklikleri gerçekleştiğinde duyurulacaktır.  

#### Görüntü yakalama:  

Enter tuşu, dikdörtgen ile sınırlandırılmış ekran alanının görüntüsünü yakalar, bir dosyaya kaydedilir ve çıkar.  

Escape tuşu iptal eder ve çıkar.  

### Ayarlar:  

NVDA tercihlerinde, ayarlarda aşağıdaki seçenekler yapılandırılabilir:  

* Dosyaların kaydedileceği klasör. Varsayılan olarak kullanıcının belgeler klasörüdür.  
* Görüntü dosyası biçimi.  
* Kaydettikten sonraki eylem (hiçbir şey yapma, klasörü aç veya dosyayı aç).  
* Her hareket için piksel sayısı.  