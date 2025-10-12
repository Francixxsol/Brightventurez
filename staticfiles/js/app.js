document.addEventListener("DOMContentLoaded", function(){
  // reviews carousel drag
  const car = document.getElementById('reviewsCarousel');
  if(car){
    let isDown=false, startX, scrollLeft;
    car.addEventListener('mousedown', e=>{ isDown=true; startX=e.pageX - car.offsetLeft; scrollLeft=car.scrollLeft;});
    car.addEventListener('mouseleave', ()=> isDown=false);
    car.addEventListener('mouseup', ()=> isDown=false);
    car.addEventListener('mousemove', e=>{ if(!isDown) return; e.preventDefault(); const x=e.pageX - car.offsetLeft; const walk=(x-startX)*2; car.scrollLeft = scrollLeft - walk; });

    // autoplay
    let auto=0;
    setInterval(()=>{ car.scrollBy({left:220, behavior:'smooth'}); },3000);
  }
});
